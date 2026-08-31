"""Window selection must fail closed; no real UI is touched by these tests."""

from types import SimpleNamespace
from unittest.mock import Mock
import unittest
from mcp_windows import inspect_window, guarded_point, find_control


class WindowScope(unittest.TestCase):
    def setUp(self):
        self.native = Mock()
        self.native.IsWindow.return_value = True
        self.native.GetWindowText.return_value = "Disposable fixture"
        self.desktop = Mock()
        self.desktop.tree.get_state.return_value = SimpleNamespace(
            status=True, semantic_tree_to_string=lambda: "fixture", interactive_elements_to_string=lambda: "field"
        )

    def test_only_explicit_window_is_read_without_focus_or_other_window_enumeration(self):
        self.assertEqual(inspect_window(self.desktop, self.native, 123, "Disposable fixture"), "fixture\nfield")
        self.desktop.tree.get_state.assert_called_once_with(123, [], use_dom=False)
        self.assertEqual([call[0] for call in self.native.mock_calls],
                         ["IsWindow", "GetWindowText", "GetWindowText"])

    def test_stale_or_reused_handle_does_not_inspect_another_window(self):
        self.native.GetWindowText.return_value = "User's unsaved project"
        with self.assertRaises(ValueError):
            inspect_window(self.desktop, self.native, 123, "Disposable fixture")
        self.desktop.tree.get_state.assert_not_called()

    def test_invalid_handle_and_empty_title_are_rejected(self):
        for handle, title in [(True, "fixture"), (-1, "fixture"), (123, "")]:
            with self.assertRaises(ValueError):
                inspect_window(self.desktop, self.native, handle, title)
        self.desktop.tree.get_state.assert_not_called()

    def test_changed_title_during_capture_discards_result(self):
        self.native.GetWindowText.side_effect = ["Disposable fixture", "Other project"]
        with self.assertRaises(ValueError):
            inspect_window(self.desktop, self.native, 123, "Disposable fixture")

    def prepare_point(self):
        self.native.IsWindowVisible.return_value = True
        self.native.IsIconic.return_value = False
        self.native.GetForegroundWindow.return_value = 123
        self.native.GetWindowRect.return_value = (10, 20, 100, 200)
        self.native.WindowFromPoint.return_value = 456
        self.native.GetAncestor.return_value = 123

    def test_guard_rejects_covered_point_without_input(self):
        self.prepare_point()
        self.native.GetAncestor.return_value = 999
        with self.assertRaises(ValueError):
            guarded_point(self.native, 123, "Disposable fixture", 50, 80)

    def test_guard_rejects_outside_point(self):
        self.prepare_point()
        with self.assertRaises(ValueError):
            guarded_point(self.native, 123, "Disposable fixture", 101, 80)
        self.native.WindowFromPoint.assert_not_called()

    def test_focus_refusal_fails_without_attach_or_input(self):
        self.prepare_point()
        self.native.GetForegroundWindow.return_value = 999
        self.native.SetForegroundWindow.side_effect = OSError("refused")
        with self.assertRaises(ValueError):
            guarded_point(self.native, 123, "Disposable fixture", 50, 80)
        self.native.WindowFromPoint.assert_not_called()
        self.assertFalse(any("Attach" in c[0] for c in self.native.mock_calls))

    def test_visible_point_is_accepted_without_changing_existing_focus(self):
        self.prepare_point()
        self.assertEqual(guarded_point(self.native, 123, "Disposable fixture", 50, 80), (50, 80))
        self.native.SetForegroundWindow.assert_not_called()

    def prepare_controls(self):
        self.prepare_point()
        self.uia = Mock()
        self.control = SimpleNamespace(
            ControlTypeName="EditControl", Name="Acceptance input", IsEnabled=True,
            IsOffscreen=False, IsPassword=False,
            GetTopLevelControl=lambda: SimpleNamespace(NativeWindowHandle=123),
        )
        self.uia.WalkControl.return_value = [(self.control, 1)]

    def resolve_control(self):
        return find_control(self.native, self.uia, 123, "Disposable fixture", "Acceptance input", "EditControl")

    def test_accessibility_target_is_unique_and_does_not_change_focus(self):
        self.prepare_controls()
        self.assertIs(self.resolve_control(), self.control)
        self.uia.ControlFromHandle.assert_called_once_with(123)
        self.native.SetForegroundWindow.assert_not_called()

    def test_duplicate_control_names_are_refused(self):
        self.prepare_controls()
        self.uia.WalkControl.return_value = [(self.control, 1), (self.control, 1)]
        with self.assertRaises(ValueError):
            self.resolve_control()

    def test_accessibility_control_from_another_window_is_refused(self):
        self.prepare_controls()
        self.control.GetTopLevelControl = lambda: SimpleNamespace(NativeWindowHandle=999)
        with self.assertRaises(ValueError):
            self.resolve_control()

    def test_disabled_offscreen_and_password_fields_are_refused(self):
        for attribute, value in [("IsEnabled", False), ("IsOffscreen", True), ("IsPassword", True)]:
            self.prepare_controls()
            setattr(self.control, attribute, value)
            with self.assertRaises(ValueError):
                self.resolve_control()

    def test_wrong_control_type_cannot_match(self):
        self.prepare_controls()
        self.control.ControlTypeName = "ButtonControl"
        with self.assertRaises(ValueError):
            self.resolve_control()

    def test_incomplete_search_at_element_budget_never_acts(self):
        self.prepare_controls()
        other = SimpleNamespace(ControlTypeName="TextControl", Name="Other")
        self.uia.WalkControl.return_value = [(self.control, 1)] + [(other, 1)] * 500
        with self.assertRaises(ValueError):
            self.resolve_control()
