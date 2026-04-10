"""Tests for GUI components."""

import pytest
from PySide6.QtWidgets import QAbstractItemView
from PySide6.QtCore import Qt

from gui.components import MultiModelSelector
from src.config import CDJ_MODELS


@pytest.fixture
def selector(app):
    """Create MultiModelSelector instance for testing."""
    return MultiModelSelector()


class TestMultiModelSelector:
    """Tests for MultiModelSelector component."""

    def test_initialization(self, selector):
        """Test that selector initializes with all models selected."""
        assert len(selector.selected_keys()) == 10
        assert selector.display_label.text() == "All Models"

    def test_initial_keys_match_cdj_models(self, selector):
        """Test that all CDJ models are present."""
        from src.config import CDJ_MODELS
        assert set(selector.selected_keys()) == set(CDJ_MODELS.keys())

    def test_set_selected_with_multiple_models(self, selector):
        """Test setting multiple models as selected."""
        selector.set_selected(['cdj-3000', 'cdj-2000nxs2'])
        assert len(selector.selected_keys()) == 2
        assert set(selector.selected_keys()) == {'cdj-3000', 'cdj-2000nxs2'}

    def test_set_selected_with_single_model(self, selector):
        """Test setting a single model as selected."""
        selector.set_selected(['cdj-400'])
        assert len(selector.selected_keys()) == 1
        assert selector.selected_keys() == ['cdj-400']

    def test_set_selected_with_empty_list(self, selector):
        """Test clearing selection with empty list."""
        selector.set_selected([])
        assert len(selector.selected_keys()) == 0
        assert selector.display_label.text() == "No Models"

    def test_clear_selection(self, selector):
        """Test clear_selection method."""
        selector.clear_selection()
        assert len(selector.selected_keys()) == 0
        assert selector.display_label.text() == "No Models"

    def test_select_all(self, selector):
        """Test select_all method."""
        selector.clear_selection()
        selector.select_all()
        assert len(selector.selected_keys()) == 10
        assert selector.display_label.text() == "All Models"

    def test_selected_displays(self, selector):
        """Test that selected_displays returns correct names."""
        selector.set_selected(['cdj-3000', 'cdj-400'])
        displays = selector.selected_displays()
        assert len(displays) == 2
        assert 'CDJ-3000' in displays
        assert 'CDJ-400' in displays

    def test_display_text_all_models(self, selector):
        """Test display text when all models are selected."""
        selector.select_all()
        assert selector.display_label.text() == "All Models"

    def test_display_text_no_models(self, selector):
        """Test display text when no models are selected."""
        selector.clear_selection()
        assert selector.display_label.text() == "No Models"

    def test_display_text_single_model(self, selector):
        """Test display text shows model name with single selection."""
        selector.set_selected(['cdj-850'])
        assert selector.display_label.text() == "CDJ-850"

    def test_display_text_multiple_models(self, selector):
        """Test display text shows count with multiple selections."""
        selector.set_selected(['cdj-3000', 'cdj-400', 'cdj-850'])
        assert selector.display_label.text() == "3 Models"

    def test_tooltip_contains_selected_models(self, selector):
        """Test that tooltip shows full list of selected models."""
        selector.set_selected(['cdj-3000', 'cdj-400'])
        tooltip = selector.display_label.toolTip()
        assert 'CDJ-3000' in tooltip
        assert 'CDJ-400' in tooltip

    def test_tooltip_empty_when_no_selection(self, selector):
        """Test that tooltip is empty when nothing selected."""
        selector.clear_selection()
        assert selector.display_label.toolTip() == ""

    def test_initial_selection_all_models(self, selector):
        """Test that all models are selected initially."""
        assert len(selector.selected_keys()) == len(CDJ_MODELS)
        assert set(selector.selected_keys()) == set(CDJ_MODELS.keys())

    def test_display_label_shows_all_models(self, selector):
        """Test that display label shows 'All Models' initially."""
        assert selector.display_label.text() == "All Models"

    def test_set_selected_updates_display(self, selector):
        """Test that set_selected updates the display label."""
        selector.set_selected(['cdj-3000', 'cdj-2000nxs2'])
        assert selector.display_label.text() == "2 Models"

    def test_single_model_display(self, selector):
        """Test display when only one model is selected."""
        selector.set_selected(['cdj-3000'])
        assert selector.display_label.text() == "CDJ-3000"

    def test_no_models_display(self, selector):
        """Test display when no models are selected."""
        selector.set_selected([])
        assert selector.display_label.text() == "No Models"

    def test_sorted_keys(self, selector):
        """Test that selected_keys returns sorted list."""
        selector.set_selected(['cdj-850', 'cdj-3000', 'cdj-400'])
        keys = selector.selected_keys()
        assert keys == sorted(keys)

    def test_sorted_displays(self, selector):
        """Test that selected_displays returns sorted by key."""
        selector.set_selected(['cdj-850', 'cdj-3000', 'cdj-400'])
        displays = selector.selected_displays()
        # Should be in key order: cdj-3000, cdj-400, cdj-850
        assert displays == ['CDJ-3000', 'CDJ-400', 'CDJ-850']

    def test_set_selected_overwrites_previous(self, selector):
        """Test that set_selected completely replaces previous selection."""
        selector.set_selected(['cdj-3000', 'cdj-400'])
        assert len(selector.selected_keys()) == 2
        
        selector.set_selected(['cdj-850'])
        assert len(selector.selected_keys()) == 1
        assert selector.selected_keys() == ['cdj-850']

    def test_select_all(self, selector):
        """Test select_all method."""
        selector.clear_selection()
        selector.select_all()
        assert len(selector.selected_keys()) == len(CDJ_MODELS)

    def test_clear_selection(self, selector):
        """Test clear_selection method."""
        selector.clear_selection()
        assert len(selector.selected_keys()) == 0

    def test_tooltip_with_selection(self, selector):
        """Test that tooltip shows full list of selected models."""
        selector.set_selected(['cdj-3000', 'cdj-400'])
        tooltip = selector.display_label.toolTip()
        assert "CDJ-3000" in tooltip and "CDJ-400" in tooltip

    def test_empty_tooltip(self, selector):
        """Test that tooltip is empty when no models selected."""
        selector.set_selected([])
        assert selector.display_label.toolTip() == ""
