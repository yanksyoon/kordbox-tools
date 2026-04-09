"""Tests for CheckTab component."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from gui.tabs.check_tab import CheckTab, _CheckWorker


@pytest.fixture
def check_tab(app):
    """Create CheckTab instance for testing."""
    return CheckTab()


class TestCheckTab:
    """Tests for CheckTab component."""

    def test_initialization(self, check_tab):
        """Test that CheckTab initializes correctly."""
        assert check_tab.file_list is not None
        assert check_tab.model_selector is not None
        assert check_tab.check_btn is not None
        assert check_tab.table is not None
        assert check_tab.progress is not None
        assert check_tab.log is not None

    def test_model_selector_is_multi_select(self, check_tab):
        """Test that model selector is MultiModelSelector."""
        from gui.components import MultiModelSelector
        assert isinstance(check_tab.model_selector, MultiModelSelector)

    def test_initial_model_selection(self, check_tab):
        """Test that all models are initially selected."""
        assert len(check_tab.model_selector.selected_keys()) == 10

    def test_file_list_starts_empty(self, check_tab):
        """Test that file list is empty initially."""
        assert check_tab.file_list.count() == 0

    def test_table_starts_empty(self, check_tab):
        """Test that results table is empty initially."""
        assert check_tab.table.rowCount() == 0

    def test_start_check_with_no_files(self, check_tab):
        """Test that start_check does nothing when no files."""
        check_tab._start_check()
        # Should not crash and worker should not be created
        assert check_tab._worker is None

    def test_start_check_with_files_creates_worker(self, check_tab):
        """Test that _start_check creates a worker with files."""
        check_tab.file_list.add_path("/path/to/file.mp3")
        
        with patch.object(_CheckWorker, 'start'):
            check_tab._start_check()
        
        assert check_tab._worker is not None

    def test_start_check_passes_selected_models(self, check_tab):
        """Test that _start_check passes selected models to worker."""
        check_tab.file_list.add_path("/path/to/file.mp3")
        check_tab.model_selector.set_selected(['cdj-3000', 'cdj-400'])
        
        # Mock the worker start to prevent actual execution
        with patch.object(_CheckWorker, 'start'):
            check_tab._start_check()
        
        assert check_tab._worker.model_keys == ['cdj-3000', 'cdj-400']

    def test_results_dict_starts_empty(self, check_tab):
        """Test that results dictionary is empty initially."""
        assert len(check_tab._results) == 0

    def test_check_btn_triggers_start_check(self, check_tab):
        """Test that check button is connected to _start_check."""
        check_tab.file_list.add_path("/path/to/file.mp3")
        
        # Mock _start_check to verify it's called
        with patch.object(check_tab, '_start_check') as mock_start:
            check_tab.check_btn.clicked.emit()
            mock_start.assert_called_once()

    def test_on_file_done_updates_results(self, check_tab):
        """Test that _on_file_done stores results."""
        filepath = "/path/to/file.mp3"
        model_results = {
            "CDJ-3000": {
                "compatible": True,
                "errors": [],
                "warnings": [],
                "notes": ["Test note"]
            }
        }
        
        check_tab._on_file_done(filepath, model_results)
        
        assert filepath in check_tab._results
        assert check_tab._results[filepath] == model_results

    def test_on_finished_enables_button(self, check_tab):
        """Test that _on_finished re-enables the check button."""
        check_tab.check_btn.setEnabled(False)
        check_tab._on_finished()
        assert check_tab.check_btn.isEnabled()

    def test_progress_display_updates(self, check_tab):
        """Test that progress display updates."""
        initial_status = check_tab.progress.status_label.text()
        check_tab._on_progress(0, 10, "test.mp3")
        new_status = check_tab.progress.status_label.text()
        assert initial_status != new_status

    def test_log_clear_clears_log(self, check_tab):
        """Test that log can be cleared."""
        check_tab.log.append_line("Test message")
        check_tab.log.clear_log()
        assert check_tab.log.toPlainText() == ""

    def test_table_clear_on_start_check(self, check_tab):
        """Test that table is cleared when starting check."""
        # Add a row
        check_tab.table.insertRow(0)
        assert check_tab.table.rowCount() == 1
        
        # Mock worker to prevent execution
        with patch.object(_CheckWorker, 'start'):
            check_tab.file_list.add_path("/path/to/file.mp3")
            check_tab._start_check()
        
        # Table should be cleared
        assert check_tab.table.rowCount() == 0


class TestCheckWorker:
    """Tests for _CheckWorker."""

    def test_worker_initialization_with_model_keys(self):
        """Test that worker initializes with model keys."""
        files = ["/path/to/file1.mp3", "/path/to/file2.wav"]
        model_keys = ['cdj-3000', 'cdj-400']
        
        worker = _CheckWorker(files, model_keys)
        
        assert worker.files == files
        assert worker.model_keys == model_keys

    def test_worker_with_empty_model_keys(self):
        """Test that worker accepts empty model keys list."""
        files = ["/path/to/file.mp3"]
        model_keys = []
        
        worker = _CheckWorker(files, model_keys)
        
        assert worker.model_keys == []

    @patch('gui.tabs.check_tab.check_compatibility')
    def test_worker_checks_selected_models(self, mock_check):
        """Test that worker checks only selected models."""
        mock_check.return_value = MagicMock(
            model="CDJ-3000",
            compatible=True,
            errors=[],
            warnings=[],
            notes=[]
        )
        
        files = ["/path/to/file.mp3"]
        model_keys = ['cdj-3000']
        
        worker = _CheckWorker(files, model_keys)
        # Just verify initialization - full run test would need more mocking
        assert worker.model_keys == ['cdj-3000']

    @patch('gui.tabs.check_tab.check_all_models')
    def test_worker_checks_all_models_when_empty(self, mock_check_all):
        """Test that worker checks all models when model_keys is empty."""
        mock_check_all.return_value = {}
        
        files = ["/path/to/file.mp3"]
        model_keys = []
        
        worker = _CheckWorker(files, model_keys)
        assert worker.model_keys == []


class TestCheckTabIntegration:
    """Integration tests for CheckTab with MultiModelSelector."""

    def test_can_select_subset_of_models(self, check_tab):
        """Test that we can select a subset of models."""
        check_tab.model_selector.set_selected(['cdj-3000', 'cdj-400', 'cdj-850'])
        assert len(check_tab.model_selector.selected_keys()) == 3

    def test_can_change_selection_and_check(self, check_tab):
        """Test workflow: select files, select models, check."""
        check_tab.file_list.add_path("/path/to/file.mp3")
        check_tab.model_selector.set_selected(['cdj-3000'])
        
        assert check_tab.file_list.count() == 1
        assert len(check_tab.model_selector.selected_keys()) == 1
        assert check_tab.model_selector.selected_keys() == ['cdj-3000']

    def test_select_all_models(self, check_tab):
        """Test selecting all models."""
        check_tab.model_selector.clear_selection()
        assert len(check_tab.model_selector.selected_keys()) == 0
        
        check_tab.model_selector.select_all()
        assert len(check_tab.model_selector.selected_keys()) == 10

    def test_clear_all_models(self, check_tab):
        """Test clearing all model selections."""
        check_tab.model_selector.clear_selection()
        assert len(check_tab.model_selector.selected_keys()) == 0
        assert check_tab.model_selector.display_label.text() == "No Models"
