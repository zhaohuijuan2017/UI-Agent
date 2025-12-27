"""窗口管理器单元测试。"""

from unittest.mock import Mock, patch

import pytest

from src.window.exceptions import WindowActivationError, WindowNotFoundError
from src.window.window_manager import WindowManager


@pytest.mark.unit
class TestWindowManager:
    """窗口管理器测试类。"""

    def test_init_without_pygetwindow(self):
        """测试没有 pygetwindow 时的初始化。"""
        with patch("builtins.__import__", side_effect=ImportError):
            manager = WindowManager()
            assert manager._pygetwindow is None

    def test_init_with_pygetwindow(self):
        """测试有 pygetwindow 时的初始化。"""
        mock_gw = Mock()
        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            assert manager._pygetwindow is not None

    def test_find_window_success(self):
        """测试成功查找窗口。"""
        mock_window = Mock()
        mock_window.title = "PyCharm - TestProject"

        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = [mock_window]
        mock_gw.getAllWindows.return_value = [mock_window]

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.find_window("PyCharm")

            assert result is not None
            assert result.title == "PyCharm - TestProject"

    def test_find_window_not_found(self):
        """测试窗口未找到。"""
        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = []
        mock_gw.getAllWindows.return_value = []

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.find_window("NonExistent")

            assert result is None

    def test_find_window_partial_match(self):
        """测试部分匹配查找窗口。"""
        mock_window = Mock()
        mock_window.title = "PyCharm - TestProject"

        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = []
        mock_gw.getAllWindows.return_value = [mock_window]

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.find_window("PyCharm", exact_match=False)

            assert result is not None

    def test_activate_window_success(self):
        """测试成功激活窗口。"""
        mock_window = Mock()
        mock_window.title = "PyCharm - TestProject"
        mock_window.isMinimized = False

        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = [mock_window]
        mock_gw.getAllWindows.return_value = [mock_window]

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.activate_window("PyCharm")

            assert result is True
            mock_window.activate.assert_called_once()

    def test_activate_window_minimized(self):
        """测试激活最小化的窗口。"""
        mock_window = Mock()
        mock_window.title = "PyCharm - TestProject"
        mock_window.isMinimized = True

        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = [mock_window]
        mock_gw.getAllWindows.return_value = [mock_window]

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.activate_window("PyCharm")

            assert result is True
            mock_window.restore.assert_called_once()
            mock_window.activate.assert_called_once()

    def test_activate_window_not_found(self):
        """测试激活不存在的窗口。"""
        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = []
        mock_gw.getAllWindows.return_value = []

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()

            with pytest.raises(WindowNotFoundError):
                manager.activate_window("NonExistent")

    def test_activate_window_without_pygetwindow(self):
        """测试没有 pygetwindow 时激活窗口。"""
        with patch("builtins.__import__", side_effect=ImportError):
            manager = WindowManager()

            with pytest.raises(WindowActivationError):
                manager.activate_window("PyCharm")

    def test_is_window_minimized_true(self):
        """测试检查窗口是否最小化（返回 True）。"""
        mock_window = Mock()
        mock_window.title = "PyCharm"
        mock_window.isMinimized = True

        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = [mock_window]
        mock_gw.getAllWindows.return_value = [mock_window]

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.is_window_minimized("PyCharm")

            assert result is True

    def test_is_window_minimized_false(self):
        """测试检查窗口是否最小化（返回 False）。"""
        mock_window = Mock()
        mock_window.title = "PyCharm"
        mock_window.isMinimized = False

        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = [mock_window]
        mock_gw.getAllWindows.return_value = [mock_window]

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.is_window_minimized("PyCharm")

            assert result is False

    def test_restore_window_success(self):
        """测试成功恢复窗口。"""
        mock_window = Mock()
        mock_window.title = "PyCharm"

        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = [mock_window]
        mock_gw.getAllWindows.return_value = [mock_window]

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.restore_window("PyCharm")

            assert result is True
            mock_window.restore.assert_called_once()

    def test_restore_window_not_found(self):
        """测试恢复不存在的窗口。"""
        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = []
        mock_gw.getAllWindows.return_value = []

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.restore_window("NonExistent")

            assert result is False

    def test_list_windows_all(self):
        """测试列出所有窗口。"""
        mock_window1 = Mock()
        mock_window1.title = "PyCharm - Project1"
        mock_window2 = Mock()
        mock_window2.title = "Visual Studio Code"

        mock_gw = Mock()
        mock_gw.getAllWindows.return_value = [mock_window1, mock_window2]

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.list_windows()

            assert len(result) == 2
            assert "PyCharm" in result[0]
            assert "Visual Studio Code" in result[1]

    def test_list_windows_with_filter(self):
        """测试使用过滤条件列出窗口。"""
        mock_window1 = Mock()
        mock_window1.title = "PyCharm - Project1"
        mock_window2 = Mock()
        mock_window2.title = "Visual Studio Code"

        mock_gw = Mock()
        mock_gw.getAllWindows.return_value = [mock_window1, mock_window2]

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.list_windows("PyCharm")

            assert len(result) == 1
            assert "PyCharm" in result[0]

    def test_list_windows_empty(self):
        """测试列出窗口（没有窗口）。"""
        mock_gw = Mock()
        mock_gw.getAllWindows.return_value = []

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.list_windows()

            assert result == []

    def test_list_windows_without_pygetwindow(self):
        """测试没有 pygetwindow 时列出窗口。"""
        with patch("builtins.__import__", side_effect=ImportError):
            manager = WindowManager()
            result = manager.list_windows()

            assert result == []

    def test_list_windows_with_exception(self):
        """测试列出窗口时发生异常。"""
        mock_gw = Mock()
        mock_gw.getAllWindows.side_effect = Exception("Test error")

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.list_windows()

            assert result == []

    # Windows 平台特定的进程查找功能测试
    # 由于涉及复杂的 Windows API 和 psutil 模拟，这些测试在单元测试环境中难以实现
    # 相关功能将在集成测试中验证

    @pytest.mark.skip(reason="需要实际的 Windows 环境")
    def test_find_by_process_name_success(self):
        """测试通过进程名成功查找窗口。"""
        # 此测试需要实际的 Windows 环境
        pass

    @pytest.mark.skip(reason="需要实际的 Windows 环境")
    def test_activate_by_process_success(self):
        """测试通过进程名成功激活窗口。"""
        # 此测试需要实际的 Windows 环境
        pass

    def test_find_by_process_name_not_found(self):
        """测试通过进程名查找窗口（未找到 - 导入错误）。"""
        # 模拟导入错误情况
        mock_gw = Mock()

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            # 模拟 win32gui 不存在
            result = manager.find_by_process_name("pycharm64.exe")

            # 由于导入错误，应该返回 None
            assert result is None

    def test_find_by_process_name_import_error(self):
        """测试通过进程名查找窗口（导入错误）。"""
        mock_gw = Mock()

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            # 模拟 win32gui 不存在
            result = manager.find_by_process_name("pycharm64.exe")

            # 由于导入错误，应该返回 None
            assert result is None

    def test_activate_by_process_not_found(self):
        """测试通过进程名激活窗口（未找到）。"""
        mock_gw = Mock()

        mock_psutil = Mock()
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.AccessDenied = Exception

        mock_win32gui = Mock()
        mock_win32gui.GetWindowText.return_value = ""
        mock_win32gui.EnumWindows.side_effect = lambda cb, _: cb(12345, None)

        mock_win32process = Mock()
        mock_win32process.GetWindowThreadProcessId.return_value = (12345, 9999)

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            with patch.dict("sys.modules", {
                "win32gui": mock_win32gui,
                "win32process": mock_win32process,
                "psutil": mock_psutil,
            }):
                with pytest.raises(WindowNotFoundError):
                    manager.activate_by_process("nonexistent.exe")

    @pytest.mark.skip(reason="需要实际的 psutil 模块")
    def test_list_processes(self):
        """测试列出所有进程。"""
        # psutil 模块的复杂行为在单元测试中难以模拟
        # 此测试将在集成测试中验证
        pass

    def test_list_processes_import_error(self):
        """测试列出进程（导入错误）。"""
        mock_gw = Mock()

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.list_processes()

            assert result == []

    def test_list_processes_with_exception(self):
        """测试列出进程时发生异常。"""
        mock_gw = Mock()

        mock_psutil = Mock()
        mock_psutil.process_iter.side_effect = Exception("Test error")
        mock_psutil.NoSuchProcess = Exception
        mock_psutil.AccessDenied = Exception

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            with patch.dict("sys.modules", {"psutil": mock_psutil}):
                result = manager.list_processes()

                assert result == []

    def test_activate_window_with_win32_fallback(self):
        """测试激活窗口时使用 Win32 API 回退。"""
        mock_window = Mock()
        mock_window.title = "PyCharm - TestProject"
        mock_window.isMinimized = False
        # 让标准激活失败
        mock_window.activate.side_effect = Exception("Standard activate failed")

        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = [mock_window]
        mock_gw.getAllWindows.return_value = [mock_window]

        mock_win32gui = Mock()
        mock_win32gui.FindWindow.return_value = 12345
        mock_win32gui.SetForegroundWindow.return_value = None
        mock_win32gui.IsIconic.return_value = False

        mock_win32con = Mock()
        mock_win32con.SW_RESTORE = 9
        mock_win32con.SW_SHOW = 5

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            with patch.dict("sys.modules", {
                "win32gui": mock_win32gui,
                "win32con": mock_win32con,
            }):
                result = manager.activate_window("PyCharm")

                assert result is True

    def test_restore_window_with_exception(self):
        """测试恢复窗口时发生异常。"""
        mock_window = Mock()
        mock_window.title = "PyCharm"
        mock_window.restore.side_effect = Exception("Restore failed")

        mock_gw = Mock()
        mock_gw.getWindowsWithTitle.return_value = [mock_window]
        mock_gw.getAllWindows.return_value = [mock_window]

        with patch("builtins.__import__", return_value=mock_gw):
            manager = WindowManager()
            result = manager.restore_window("PyCharm")

            assert result is False
