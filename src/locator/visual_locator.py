"""视觉 UI 定位器。"""

import json
import re
from typing import Optional

from PIL import Image
from zhipuai import ZhipuAI

from src.locator.screenshot import ScreenshotCapture
from src.models.element import UIElement


class CoordinateCalibrator:
    """坐标校准器。"""

    def __init__(self, offset_x: int = 0, offset_y: int = 0):
        """初始化坐标校准器。

        Args:
            offset_x: X 轴偏移量
            offset_y: Y 轴偏移量
        """
        self.offset_x = offset_x
        self.offset_y = offset_y

    def calibrate(self, bbox: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        """校准边界框坐标。

        Args:
            bbox: 原始边界框 (x1, y1, x2, y2)

        Returns:
            校准后的边界框
        """
        x1, y1, x2, y2 = bbox
        return (x1 + self.offset_x, y1 + self.offset_y, x2 + self.offset_x, y2 + self.offset_y)

    @classmethod
    def from_config(cls, offset: list[int] | None) -> "CoordinateCalibrator":
        """从配置创建校准器。

        Args:
            offset: 偏移量配置 [x_offset, y_offset]

        Returns:
            坐标校准器实例
        """
        if offset and len(offset) >= 2:
            return cls(offset[0], offset[1])
        return cls(0, 0)

# 尝试导入 OCR 库
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class VisualLocator:
    """视觉 UI 定位器。"""

    def __init__(
        self,
        api_key: str,
        model: str = "glm-4v-flash",
        screenshot_capture: ScreenshotCapture | None = None,
        vision_enabled: bool = True,
        base_url: str | None = None,
        monitor_index: int = 0,
    ) -> None:
        """初始化视觉定位器。

        Args:
            api_key: 智谱 AI API Key
            model: 使用的模型名称
            screenshot_capture: 截图捕获器（可选）
            vision_enabled: 是否启用大模型视觉识别（默认 True）
            base_url: LLM API Base URL（可选，用于自定义代理）
            monitor_index: 默认显示器索引（默认 0 = 所有显示器合并）
                - 0: 整个虚拟屏幕（所有显示器合并）
                - 1: 第一个显示器
                - 2: 第二个显示器
                - 以此类推...
        """
        # 初始化 LLM 客户端（支持自定义 base_url）
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = ZhipuAI(**client_kwargs)
        self.model = model
        self.screenshot_capture = screenshot_capture
        self._vision_enabled = vision_enabled
        self._monitor_index = monitor_index

        # 定位结果缓存
        self._cache: dict[str, list[UIElement]] = {}

        # 坐标校准器
        self.calibrator = CoordinateCalibrator.from_config(None)  # 默认无偏移

    def set_monitor_index(self, monitor_index: int) -> None:
        """设置默认显示器索引。

        Args:
            monitor_index: 显示器索引
                - 0: 整个虚拟屏幕（所有显示器合并）
                - 1: 第一个显示器
                - 2: 第二个显示器
                - 以此类推...
        """
        self._monitor_index = monitor_index

    def get_monitor_index(self) -> int:
        """获取当前显示器索引。

        Returns:
            显示器索引
        """
        return self._monitor_index

    def set_coordinate_offset(self, offset: list[int] | None) -> None:
        """设置坐标偏移量。

        Args:
            offset: 偏移量 [x_offset, y_offset]
        """
        self.calibrator = CoordinateCalibrator.from_config(offset)

    def locate(
        self,
        prompt: str,
        screenshot: Image.Image | None = None,
        use_cache: bool = True,
        target_filter: str | None = None,
        use_ocr_fallback: bool = True,
        monitor_index: int | None = None,
    ) -> list[UIElement]:
        """在截图中定位 UI 元素。

        Args:
            prompt: 定位提示词
            screenshot: 截图图像，如果不提供则自动捕获
            use_cache: 是否使用缓存
            target_filter: 目标文件名/文本，用于过滤最匹配的元素
            use_ocr_fallback: 是否使用 OCR 混合定位（GLM + OCR）
            monitor_index: 显示器索引（可选，覆盖默认值）
                - 0: 整个虚拟屏幕（所有显示器合并）
                - 1: 第一个显示器
                - 2: 第二个显示器
                - 以此类推...

        Returns:
            定位到的 UI 元素列表
        """
        # 如果没有提供截图，尝试捕获
        if screenshot is None and self.screenshot_capture:
            idx = monitor_index if monitor_index is not None else self._monitor_index
            screenshot = self.screenshot_capture.capture_fullscreen(monitor_index=idx)

        if screenshot is None:
            return []

        # 如果视觉识别被禁用，直接使用 OCR
        if not self._vision_enabled:
            print(f"[定位] 视觉识别已禁用，使用 OCR 定位,关键字为{target_filter}")
            if target_filter:
                return self._locate_with_ocr(screenshot, target_filter)
            # 如果没有目标过滤，尝试全图 OCR 获取所有文本
            return self._locate_with_ocr(screenshot, "")

        # 如果有目标过滤且支持 OCR，使用混合定位方法
        if use_ocr_fallback and target_filter and EASYOCR_AVAILABLE:
            print(f"[定位] 使用混合定位方法 (GLM + OCR),关键字为{target_filter}")
            elements = self._locate_hybrid(screenshot, prompt, target_filter)
        else:
            # 检查缓存
            cache_key = f"{prompt}:{hash(screenshot.tobytes())}"
            if use_cache and cache_key in self._cache:
                elements = self._cache[cache_key]
            else:
                # 调用视觉 API
                elements = self._locate_with_vision(screenshot, prompt)
                # 缓存结果
                if use_cache:
                    self._cache[cache_key] = elements

            # 如果指定了目标过滤，选择最匹配的元素
            if target_filter and elements:
                elements = self._filter_by_target(elements, target_filter)

        return elements

    def _filter_by_target(self, elements: list[UIElement], target: str) -> list[UIElement]:
        """根据目标名称过滤和排序元素。

        Args:
            elements: 元素列表
            target: 目标名称

        Returns:
            过滤后的元素列表
        """
        # 计算每个元素与目标名称的匹配度
        scored_elements = []
        for elem in elements:
            score = self._calculate_match_score(elem.description, target)
            scored_elements.append((score, elem))
            print(f"[匹配] '{elem.description}' -> {target}: 分数={score:.2f}")

        # 按匹配度降序排序
        scored_elements.sort(key=lambda x: x[0], reverse=True)

        # 只返回匹配度 > 0.5 的元素
        result = [elem for score, elem in scored_elements if score > 0.5]

        if not result and scored_elements:
            # 如果没有高匹配度的，返回最高分的
            best_score, best_elem = scored_elements[0]
            print(f"[匹配] 最佳匹配分数较低 ({best_score:.2f})，使用: {best_elem.description}")
            return [best_elem]

        return result if result else []

    def _calculate_match_score(self, description: str, target: str) -> float:
        """计算描述与目标的匹配度。

        Args:
            description: 元素描述
            target: 目标名称

        Returns:
            匹配度分数 (0-1)
        """
        desc_lower = description.lower()
        target_lower = target.lower()

        # 完全匹配
        if target_lower in desc_lower:
            # 精确匹配得分更高
            if desc_lower == target_lower:
                return 1.0
            # 包含目标名称
            return 0.9

        # 部分匹配（检查分词）
        target_parts = target_lower.replace(".", " ").replace("_", " ").split()
        match_count = sum(1 for part in target_parts if part in desc_lower)
        if match_count > 0:
            return match_count / len(target_parts) * 0.7

        return 0.0

    def _fix_json_format(self, json_str: str) -> str:
        """修复 JSON 字符串中的常见格式问题。

        Args:
            json_str: 可能存在格式问题的 JSON 字符串

        Returns:
            修复后的 JSON 字符串
        """
        import re

        # 首先尝试直接解析，如果成功则返回
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            pass

        # 修复策略1: 处理字段值中未转义的双引号
        # 例如: "description": "文件 "main.py"" -> "description": "文件 \"main.py\""

        def fix_field_value(match):
            """修复字段值中的双引号。"""
            before_value = match.group(1)  # "key": "
            value_content = match.group(2)  # 值内容（可能包含未转义的引号）
            after_value = match.group(3)  # 结尾的 "

            # 统计：如果值内包含未配对的引号，需要转义
            # 策略：将值内的 " 替换为 \"
            fixed_content = value_content.replace('"', '\\"')
            return f'{before_value}{fixed_content}{after_value}'

        # 使用正则表达式匹配可能存在问题的字段值
        # 模式: "key": "value...value"，其中 value 内部可能有未转义的引号
        # 这是比较复杂的情况，使用更简单的方法

        # 简单方法：逐行处理
        lines = json_str.split('\n')
        fixed_lines = []

        for line in lines:
            # 检查是否包含字符串字段
            if '": "' in line:
                # 尝试修复这一行
                parts = line.split('": "')
                if len(parts) >= 2:
                    # 重建行
                    fixed_line = parts[0] + '": "'
                    rest = '": "'.join(parts[1:])

                    # 找到最后一个 " 作为值的结束
                    last_quote_pos = rest.rfind('"')
                    if last_quote_pos > 0:
                        value_part = rest[:last_quote_pos]
                        remaining = rest[last_quote_pos:]

                        # 转义值内的双引号
                        value_part = value_part.replace('"', '\\"')
                        fixed_line += value_part + remaining
                        line = fixed_line

            fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def _locate_with_vision(self, screenshot: Image, prompt: str) -> list[UIElement]:
        """使用视觉 API 定位元素。

        Args:
            screenshot: 截图图像
            prompt: 定位提示词

        Returns:
            定位到的 UI 元素列表
        """
        # 将图像转换为 base64
        import base64
        from io import BytesIO

        buffer = BytesIO()
        screenshot.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        # 构建提示词
        vision_prompt = f"""请分析截图，找到以下 UI 元素：

{prompt}

请返回 JSON 格式的结果，包含每个元素的：
1. element_type: 元素类型（button, menu, text_field, tree, dialog 等）
2. description: 元素描述（注意：禁止在描述中使用双引号，文件名用单引号包裹）
3. bbox: 边界框坐标 [x1, y1, x2, y2]（基于截图像素坐标）
4. confidence: 置信度 (0-1)

只返回 JSON 数组，不要其他内容。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}},
                            {"type": "text", "text": vision_prompt},
                        ],
                    }
                ],
                temperature=0.1,
            )

            result_text = response.choices[0].message.content.strip()

            # 清理 markdown 代码块标记
            if result_text.startswith("```json"):
                result_text = result_text[7:]  # 移除 ```json
            elif result_text.startswith("```"):
                result_text = result_text[3:]  # 移除 ```

            if result_text.endswith("```"):
                result_text = result_text[:-3]  # 移除结尾的 ```

            result_text = result_text.strip()

            # 修复 JSON 中的常见格式问题
            result_text = self._fix_json_format(result_text)

            # 解析 JSON 结果
            data = json.loads(result_text)

            elements = []
            for item in data if isinstance(data, list) else [data]:
                bbox = item.get("bbox", [])
                if len(bbox) >= 4:
                    elements.append(
                        UIElement(
                            element_type=item.get("element_type", "unknown"),
                            description=item.get("description", ""),
                            bbox=(int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])),
                            confidence=float(item.get("confidence", 0.8)),
                        )
                    )

            return elements
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            # 解析失败，返回空列表
            print(f"JSON 解析错误: {e}")
            print(f"原始内容: {result_text[:200] if 'result_text' in locals() else 'N/A'}")
            return []

    def verify(
        self,
        element: UIElement,
        screenshot: Image.Image | None = None,
        monitor_index: int | None = None,
    ) -> bool:
        """验证元素位置。

        Args:
            element: UI 元素
            screenshot: 截图图像
            monitor_index: 显示器索引（可选，覆盖默认值）

        Returns:
            是否验证通过
        """
        if screenshot is None and self.screenshot_capture:
            idx = monitor_index if monitor_index is not None else self._monitor_index
            screenshot = self.screenshot_capture.capture_fullscreen(monitor_index=idx)

        if screenshot is None:
            return False

        # 检查边界框是否在截图范围内
        width, height = screenshot.size
        x1, y1, x2, y2 = element.bbox

        return (
            0 <= x1 < x2 <= width
            and 0 <= y1 < y2 <= height
            and element.confidence >= 0.5
        )

    def locate_with_fallback(
        self,
        prompt: str,
        screenshot: Image.Image | None = None,
        fallback_bbox: tuple[int, int, int, int] | None = None,
    ) -> UIElement | None:
        """带回退机制的元素定位。

        Args:
            prompt: 定位提示词
            screenshot: 截图图像
            fallback_bbox: 回退使用的固定边界框

        Returns:
            定位到的 UI 元素，如果失败则返回回退元素
        """
        elements = self.locate(prompt, screenshot)

        if elements and elements[0].confidence >= 0.6:
            return elements[0]

        # 回退到固定坐标
        if fallback_bbox:
            return UIElement(
                element_type="fallback",
                description="回退坐标",
                bbox=fallback_bbox,
                confidence=0.5,
            )

        return None

    def _locate_with_ocr(self, screenshot: Image, target_text: str) -> list[UIElement]:
        """使用 OCR 定位元素。

        Args:
            screenshot: 截图图像
            target_text: 目标文本

        Returns:
            定位到的 UI 元素列表
        """
        if not (EASYOCR_AVAILABLE or TESSERACT_AVAILABLE):
            return []

        elements = []
        target_lower = target_text.lower()

        # 优先使用 EasyOCR（更准确）
        if EASYOCR_AVAILABLE:
            try:
                # 延迟加载 Reader（初始化耗时）
                if not hasattr(self, '_ocr_reader'):
                    self._ocr_reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)

                import numpy as np
                # 转换 PIL 图像为 numpy 数组
                img_array = np.array(screenshot)

                # 执行 OCR
                results = self._ocr_reader.readtext(img_array)

                for (bbox, text, confidence) in results:
                    # bbox 格式: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                    x1 = int(min(p[0] for p in bbox))
                    y1 = int(min(p[1] for p in bbox))
                    x2 = int(max(p[0] for p in bbox))
                    y2 = int(max(p[1] for p in bbox))

                    # 检查文本是否包含目标文本
                    if target_lower in text.lower():
                        elements.append(
                            UIElement(
                                element_type="ocr_text",
                                description=f"OCR识别文本: {text}",
                                bbox=(x1, y1, x2, y2),
                                confidence=float(confidence),
                            )
                        )
                        print(f"[OCR] 找到匹配文本 '{text}' at bbox=({x1}, {y1}, {x2}, {y2})")

                return elements

            except Exception as e:
                print(f"[OCR] EasyOCR 定位失败: {e}")

        # 回退到 Tesseract
        if TESSERACT_AVAILABLE:
            try:
                import numpy as np

                # 使用 pytesseract 获取文本和坐标
                data = pytesseract.image_to_data(
                    screenshot,
                    output_type=pytesseract.Output.DICT,
                    lang='eng+chi_sim'
                )

                n_boxes = len(data['text'])
                for i in range(n_boxes):
                    text = data['text'][i].strip()
                    conf = int(data['conf'][i])

                    if text and target_lower in text.lower() and conf > 0:
                        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                        elements.append(
                            UIElement(
                                element_type="ocr_text",
                                description=f"OCR识别文本: {text}",
                                bbox=(x, y, x + w, y + h),
                                confidence=min(conf / 100.0, 1.0),
                            )
                        )
                        print(f"[OCR] 找到匹配文本 '{text}' at bbox=({x}, {y}, {x+w}, {y+h})")

            except Exception as e:
                print(f"[OCR] Tesseract 定位失败: {e}")

        return elements

    def _locate_with_ocr_in_region(
        self,
        screenshot: Image,
        target_text: str,
        search_region: tuple[int, int, int, int] | None = None,
    ) -> list[UIElement]:
        """在指定区域内使用 OCR 定位元素。

        Args:
            screenshot: 截图图像
            target_text: 目标文本
            search_region: 搜索区域 (x1, y1, x2, y2)，如果为 None 则搜索全图

        Returns:
            定位到的 UI 元素列表
        """
        if not EASYOCR_AVAILABLE:
            return []

        try:
            # 如果指定了搜索区域，裁剪图像
            if search_region:
                x1, y1, x2, y2 = search_region
                crop_img = screenshot.crop((x1, y1, x2, y2))
                offset_x, offset_y = x1, y1
                print(f"[OCR] 在区域 ({x1}, {y1}, {x2}, {y2}) 内搜索，裁剪图大小: {crop_img.size}")
            else:
                crop_img = screenshot
                offset_x, offset_y = 0, 0
                print(f"[OCR] 全图搜索，图像大小: {crop_img.size}")

            # 延迟加载 Reader
            if not hasattr(self, '_ocr_reader'):
                print(f"[OCR] 初始化 EasyOCR Reader...")
                self._ocr_reader = easyocr.Reader(['en', 'ch_sim'], gpu=False)

            import numpy as np
            img_array = np.array(crop_img)
            print(f"[OCR] 开始 OCR 识别，图像数组形状: {img_array.shape}")

            results = self._ocr_reader.readtext(img_array)
            print(f"[OCR] OCR 识别完成，返回 {len(results)} 个结果")

            elements = []
            target_lower = target_text.lower()

            # 调试：显示所有识别到的文本
            if results:
                print(f"[OCR] 识别到的文本块:")
                for (bbox, text, confidence) in results[:10]:  # 只显示前 10 个
                    print(f"       - '{text}' (置信度={confidence:.2f})")
            else:
                print(f"[OCR] 未识别到任何文本")

            for (bbox, text, confidence) in results:
                # 降低置信度阈值以捕获更多可能的匹配
                if confidence > 0.1 and target_lower in text.lower():
                    # bbox 格式: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
                    x_coords = [p[0] for p in bbox]
                    y_coords = [p[1] for p in bbox]

                    x1_local = int(min(x_coords))
                    y1_local = int(min(y_coords))
                    x2_local = int(max(x_coords))
                    y2_local = int(max(y_coords))

                    # 加上偏移量
                    x1_final = x1_local + offset_x
                    y1_final = y1_local + offset_y
                    x2_final = x2_local + offset_x
                    y2_final = y2_local + offset_y

                    elements.append(
                        UIElement(
                            element_type="ocr_text",
                            description=f"OCR识别文本: {text}",
                            bbox=(x1_final, y1_final, x2_final, y2_final),
                            confidence=float(confidence),
                        )
                    )
                    print(f"[OCR] 找到 '{text}' at bbox=({x1_final}, {y1_final}, {x2_final}, {y2_final}), 置信度={confidence:.2f}")

            return elements

        except Exception as e:
            print(f"[OCR] 区域定位失败: {e}")
            return []

    def _locate_hybrid(
        self,
        screenshot: Image,
        prompt: str,
        target_text: str,
    ) -> list[UIElement]:
        """混合方法：先用 GLM 获取大致区域，再用 OCR 精确定位。

        Args:
            screenshot: 截图图像
            prompt: GLM 定位提示词
            target_text: 目标文本

        Returns:
            定位到的 UI 元素列表
        """
        # 第一步：用 GLM 获取大致区域
        glm_elements = self._locate_with_vision(screenshot, prompt)

        if not glm_elements:
            print(f"[混合定位] GLM 未找到任何元素，尝试全图 OCR...")
            return self._locate_with_ocr(screenshot, target_text)

        # 选择最匹配的 GLM 结果
        best_glm = glm_elements[0]
        print(f"[混合定位] GLM 返回 bbox={best_glm.bbox}, 置信度={best_glm.confidence}")

        # 第二步：扩大搜索区域后使用 OCR 精确定位
        x1, y1, x2, y2 = best_glm.bbox
        width, height = screenshot.size

        # 扩大搜索区域（上下左右各扩展适当距离）
        # 确保 OCR 有足够的上下文，使用更大的扩展范围
        bbox_width = x2 - x1
        bbox_height = y2 - y1
        margin_x = max(150, bbox_width * 5)  # 水平方向扩展 bbox 宽度的 5 倍，最少 150px
        margin_y = max(100, bbox_height * 5)  # 垂直方向扩展 bbox 高度的 5 倍，最少 100px

        search_region = (
            max(0, int(x1 - margin_x)),
            max(0, int(y1 - margin_y)),
            min(width, int(x2 + margin_x)),
            min(height, int(y2 + margin_y))
        )

        # 确保搜索区域有足够的最小尺寸
        region_width = search_region[2] - search_region[0]
        region_height = search_region[3] - search_region[1]
        if region_width < 200:
            search_region = (
                max(0, search_region[0] - (200 - region_width) // 2),
                search_region[1],
                min(width, search_region[2] + (200 - region_width) // 2),
                search_region[3]
            )
        if region_height < 100:
            search_region = (
                search_region[0],
                max(0, search_region[1] - (100 - region_height) // 2),
                search_region[2],
                min(height, search_region[3] + (100 - region_height) // 2)
            )

        print(f"[混合定位] 在扩大区域 {search_region} 内使用 OCR 精确定位...")

        ocr_elements = self._locate_with_ocr_in_region(screenshot, target_text, search_region)

        if ocr_elements:
            print(f"[混合定位] OCR 精确定位成功，找到 {len(ocr_elements)} 个结果")
            return ocr_elements

        # 如果区域内未找到，尝试全图 OCR
        print(f"[混合定位] 区域内未找到，尝试全图 OCR...")
        ocr_elements_full = self._locate_with_ocr_in_region(screenshot, target_text, None)

        if ocr_elements_full:
            print(f"[混合定位] 全图 OCR 找到 {len(ocr_elements_full)} 个结果")
            return ocr_elements_full

        print(f"[混合定位] OCR 未找到，使用 GLM 结果")
        return glm_elements

    def clear_cache(self) -> None:
        """清空定位缓存。"""
        self._cache.clear()
