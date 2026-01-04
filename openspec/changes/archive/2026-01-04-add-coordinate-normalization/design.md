# 设计文档: 坐标归一化还原

## 1. 架构设计

### 1.1 坐标类型定义

系统需要支持两种坐标类型:

1. **归一化坐标(Normalized Coordinates)**
   - 范围: 0-1000
   - 来源: LLM视觉API返回
   - 需要转换为实际像素坐标

2. **像素坐标(Pixel Coordinates)**
   - 范围: 0到图像实际宽度/高度
   - 来源: OCR、模板匹配等传统方法
   - 直接使用

### 1.2 检测策略

#### 启发式规则

```python
def is_normalized_coordinate(bbox: tuple[int, int, int, int], image_size: tuple[int, int]) -> bool:
    """判断是否为归一化坐标。

    Args:
        bbox: 边界框 (x1, y1, x2, y2)
        image_size: 图像尺寸 (width, height)

    Returns:
        如果是归一化坐标返回True
    """
    x1, y1, x2, y2 = bbox
    width, height = image_size

    # 规则1: 所有坐标值都在0-1000范围内
    if not all(0 <= coord <= 1000 for coord in bbox):
        return False

    # 规则2: 如果图像尺寸接近1000x1000,可能是像素坐标
    if 900 < width <= 1100 and 900 < height <= 1100:
        # 进一步检查: 如果坐标值接近图像尺寸,可能是像素坐标
        if x2 < width * 0.95:  # 归一化坐标通常不会这么接近边界
            return True

    # 规则3: 检查坐标比例是否合理
    # 归一化坐标的比例应该与实际坐标一致
    bbox_width = x2 - x1
    bbox_height = y2 - y1

    # 如果bbox宽度/高度小于图像宽度/高度的10%,可能是归一化坐标
    if bbox_width < width * 0.1 and bbox_height < height * 0.1:
        return True

    # 默认: 检查是否所有坐标都明显小于图像尺寸
    return max(x1, y1, x2, y2) < min(width, height) * 0.8
```

#### 简化策略(推荐)

考虑到实际场景:
- LLM返回的归一化坐标通常在0-1000范围
- 实际截图通常大于1000像素(高分辨率屏幕)
- OCR等传统方法返回的是真实像素坐标

简化规则:
```python
def is_normalized_coordinate(bbox: tuple[int, int, int, int], image_size: tuple[int, int]) -> bool:
    """简化判断: 如果最大坐标值小于图像最小边,认为是归一化坐标。"""
    max_coord = max(bbox)
    min_image_dim = min(image_size)
    return max_coord <= 1000 and max_coord < min_image_dim
```

### 1.3 坐标转换算法

```python
def denormalize_bbox(
    bbox: tuple[int, int, int, int],
    image_size: tuple[int, int]
) -> tuple[int, int, int, int]:
    """将归一化坐标转换为实际像素坐标。

    Args:
        bbox: 归一化边界框 (x1, y1, x2, y2), 范围0-1000
        image_size: 图像尺寸 (width, height)

    Returns:
        实际像素边界框
    """
    x1, y1, x2, y2 = bbox
    width, height = image_size

    # 使用浮点数计算提高精度
    actual_x1 = int((x1 / 1000.0) * width)
    actual_y1 = int((y1 / 1000.0) * height)
    actual_x2 = int((x2 / 1000.0) * width)
    actual_y2 = int((y2 / 1000.0) * height)

    # 确保坐标在有效范围内
    actual_x1 = max(0, min(actual_x1, width - 1))
    actual_y1 = max(0, min(actual_y1, height - 1))
    actual_x2 = max(actual_x1 + 1, min(actual_x2, width))
    actual_y2 = max(actual_y1 + 1, min(actual_y2, height))

    return (actual_x1, actual_y1, actual_x2, actual_y2)
```

## 2. 实现细节

### 2.1 修改 `_locate_with_vision` 方法

**文件**: `src/locator/visual_locator.py`

**修改位置**: 第393-402行

**当前代码**:
```python
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
```

**修改后代码**:
```python
for item in data if isinstance(data, list) else [data]:
    bbox = item.get("bbox", [])
    if len(bbox) >= 4:
        # 转换为整数元组
        bbox_tuple = (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))

        # 检测并转换归一化坐标
        image_size = screenshot.size
        if self._is_normalized_coordinate(bbox_tuple, image_size):
            bbox_tuple = self._denormalize_bbox(bbox_tuple, image_size)
            print(f"[坐标] 检测到归一化坐标 {tuple(int(bbox[i]) for i in range(4))}, "
                  f"已转换为实际坐标 {bbox_tuple}")

        elements.append(
            UIElement(
                element_type=item.get("element_type", "unknown"),
                description=item.get("description", ""),
                bbox=bbox_tuple,
                confidence=float(item.get("confidence", 0.8)),
            )
        )
```

### 2.2 添加辅助方法

在 `VisualLocator` 类中添加:

```python
@staticmethod
def _is_normalized_coordinate(
    bbox: tuple[int, int, int, int],
    image_size: tuple[int, int]
) -> bool:
    """判断是否为归一化坐标。

    归一化坐标特征:
    - 坐标值在0-1000范围内
    - 最大坐标值明显小于图像尺寸

    Args:
        bbox: 边界框 (x1, y1, x2, y2)
        image_size: 图像尺寸 (width, height)

    Returns:
        如果是归一化坐标返回True
    """
    max_coord = max(bbox)
    min_image_dim = min(image_size)

    # 简化规则: 坐标值≤1000 且小于图像最小边
    return max_coord <= 1000 and max_coord < min_image_dim

@staticmethod
def _denormalize_bbox(
    bbox: tuple[int, int, int, int],
    image_size: tuple[int, int]
) -> tuple[int, int, int, int]:
    """将归一化坐标转换为实际像素坐标。

    Args:
        bbox: 归一化边界框 (x1, y1, x2, y2), 范围0-1000
        image_size: 图像尺寸 (width, height)

    Returns:
        实际像素边界框
    """
    x1, y1, x2, y2 = bbox
    width, height = image_size

    # 转换公式: 实际坐标 = (归一化坐标 / 1000) × 图像尺寸
    actual_x1 = max(0, min(int((x1 / 1000.0) * width), width - 1))
    actual_y1 = max(0, min(int((y1 / 1000.0) * height), height - 1))
    actual_x2 = max(actual_x1 + 1, min(int((x2 / 1000.0) * width), width))
    actual_y2 = max(actual_y1 + 1, min(int((y2 / 1000.0) * height), height))

    return (actual_x1, actual_y1, actual_x2, actual_y2)
```

## 3. 边界情况处理

### 3.1 小尺寸图像

**问题**: 如果截图尺寸小于1000×1000,可能误判

**解决方案**:
```python
# 对于小尺寸图像(如缩略图),如果坐标值接近图像尺寸,认为是像素坐标
if min_image_dim < 1000:
    # 检查坐标是否在合理范围内(应该是像素坐标)
    return max_coord > min_image_dim * 0.9
```

### 3.2 精确边界

**问题**: 转换后的坐标可能超出图像边界

**解决方案**:
```python
# 转换后进行边界裁剪
actual_x1 = max(0, min(actual_x1, width - 1))
actual_y1 = max(0, min(actual_y1, height - 1))
actual_x2 = max(actual_x1 + 1, min(actual_x2, width))  # 确保至少有1像素宽度
actual_y2 = max(actual_y1 + 1, min(actual_y2, height))
```

### 3.3 浮点数精度

**问题**: 除法运算可能产生浮点数误差

**解决方案**:
- 使用浮点数进行中间计算
- 最终结果转换为整数
- 对于边界值,使用 `max(0, min(value, boundary))` 确保在范围内

## 4. 测试策略

### 4.1 单元测试

```python
def test_is_normalized_coordinate():
    """测试归一化坐标检测逻辑。"""
    # 归一化坐标案例
    assert VisualLocator._is_normalized_coordinate(
        (100, 200, 300, 400), (1920, 1080)
    ) == True

    # 像素坐标案例
    assert VisualLocator._is_normalized_coordinate(
        (500, 600, 700, 800), (800, 600)
    ) == False

def test_denormalize_bbox():
    """测试坐标转换。"""
    # 1920x1080图像
    # 归一化坐标 (500, 500, 600, 600) 应转换为 (960, 540, 1152, 648)
    result = VisualLocator._denormalize_bbox(
        (500, 500, 600, 600), (1920, 1080)
    )
    assert result == (960, 540, 1152, 648)

    # 边界情况: 坐标为1000
    result = VisualLocator._denormalize_bbox(
        (0, 0, 1000, 1000), (1920, 1080)
    )
    assert result == (0, 0, 1920, 1080)
```

### 4.2 集成测试

使用不同分辨率的截图测试:
- 1920×1080 (Full HD)
- 2560×1440 (2K)
- 3840×2160 (4K)
- 1280×720 (HD)

## 5. 性能影响

- **计算开销**: 每个bbox增加4次浮点除法和4次乘法
- **时间复杂度**: O(1),与bbox数量成正比
- **空间开销**: 无额外内存分配

**预估影响**: 可忽略不计(每次转换 < 1微秒)

## 6. 向后兼容性

- ✅ 不改变API签名
- ✅ 自动检测坐标类型
- ✅ 像素坐标直接使用,无性能损失
- ✅ 添加日志记录,便于调试

## 7. 未来扩展

如果需要更精细的
控制,可以考虑:

1. **配置项**: `vision.coordinate_format: "normalized" | "pixel" | "auto"`
2. **元数据记录**: 在 `UIElement.metadata` 中记录坐标类型
3. **性能优化**: 对于已知格式,跳过检测逻辑

当前实现使用 `"auto"` 模式,满足大部分场景需求。
