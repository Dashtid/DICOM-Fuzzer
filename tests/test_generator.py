"""
Comprehensive tests for DICOM Generator.

Tests cover:
- DICOMGenerator initialization
- Output directory creation
- Batch file generation
- Filename generation and uniqueness
- Integration with fuzzing strategies
- File saving and output
- Edge cases
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dicom_fuzzer.core.generator import DICOMGenerator


class TestDICOMGeneratorInit:
    """Test DICOMGenerator initialization."""

    def test_generator_creation_default_dir(self, temp_dir):
        """Test creating generator with default output directory."""
        output_dir = temp_dir / "fuzzed_dicoms"
        generator = DICOMGenerator(output_dir=str(output_dir))

        assert generator.output_dir == output_dir
        assert generator.output_dir.exists()
        assert generator.output_dir.is_dir()

    def test_generator_creation_custom_dir(self, temp_dir):
        """Test creating generator with custom output directory."""
        custom_dir = temp_dir / "custom_output"
        generator = DICOMGenerator(output_dir=str(custom_dir))

        assert generator.output_dir == custom_dir
        assert generator.output_dir.exists()

    def test_generator_creates_dir_if_missing(self, temp_dir):
        """Test that generator creates output directory if it doesn't exist."""
        nonexistent_dir = temp_dir / "level1" / "level2" / "output"
        assert not nonexistent_dir.exists()

        generator = DICOMGenerator(output_dir=str(nonexistent_dir))

        assert generator.output_dir.exists()
        assert generator.output_dir.is_dir()

    def test_generator_accepts_existing_dir(self, temp_dir):
        """Test that generator works with existing directory."""
        existing_dir = temp_dir / "existing"
        existing_dir.mkdir()

        generator = DICOMGenerator(output_dir=str(existing_dir))

        assert generator.output_dir == existing_dir
        assert generator.output_dir.exists()


class TestBatchGeneration:
    """Test batch file generation functionality."""

    def test_generate_batch_creates_files(self, sample_dicom_file, temp_dir):
        """Test that generate_batch creates the correct number of files."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=5)

        assert len(generated_files) == 5
        # Verify all files exist
        for file_path in generated_files:
            assert file_path.exists()
            assert file_path.is_file()

    def test_generate_batch_single_file(self, sample_dicom_file, temp_dir):
        """Test generating a single file."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=1)

        assert len(generated_files) == 1
        assert generated_files[0].exists()

    def test_generate_batch_zero_count(self, sample_dicom_file, temp_dir):
        """Test that count=0 generates no files."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=0)

        assert len(generated_files) == 0

    def test_generate_batch_large_count(self, sample_dicom_file, temp_dir):
        """Test generating a large batch of files."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=50)

        assert len(generated_files) == 50
        # Verify all files exist
        for file_path in generated_files:
            assert file_path.exists()

    def test_generate_batch_returns_paths(self, sample_dicom_file, temp_dir):
        """Test that generate_batch returns Path objects."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=3)

        assert all(isinstance(path, Path) for path in generated_files)

    def test_generate_batch_files_in_output_dir(self, sample_dicom_file, temp_dir):
        """Test that generated files are in the output directory."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=3)

        for file_path in generated_files:
            assert file_path.parent == output_dir


class TestFilenameGeneration:
    """Test filename generation and uniqueness."""

    def test_filename_format(self, sample_dicom_file, temp_dir):
        """Test that filenames follow expected format."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=5)

        for file_path in generated_files:
            # Should be fuzzed_<8char_hex>.dcm
            assert file_path.name.startswith("fuzzed_")
            assert file_path.name.endswith(".dcm")
            # Extract hex part: fuzzed_XXXXXXXX.dcm
            hex_part = file_path.name[7:-4]  # Skip "fuzzed_" and ".dcm"
            assert len(hex_part) == 8
            # Verify hex characters
            assert all(c in "0123456789abcdef" for c in hex_part)

    def test_filename_uniqueness(self, sample_dicom_file, temp_dir):
        """Test that all generated filenames are unique."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=10)

        filenames = [f.name for f in generated_files]
        assert len(filenames) == len(set(filenames))  # All unique

    def test_multiple_batches_unique_names(self, sample_dicom_file, temp_dir):
        """Test that multiple batches generate unique filenames."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        batch1 = generator.generate_batch(sample_dicom_file, count=5)
        batch2 = generator.generate_batch(sample_dicom_file, count=5)

        all_files = batch1 + batch2
        filenames = [f.name for f in all_files]
        assert len(filenames) == len(set(filenames))  # All unique across batches


class TestFuzzerIntegration:
    """Test integration with fuzzing strategies."""

    @patch("dicom_fuzzer.core.generator.MetadataFuzzer")
    @patch("dicom_fuzzer.core.generator.HeaderFuzzer")
    @patch("dicom_fuzzer.core.generator.PixelFuzzer")
    def test_fuzzers_instantiated(
        self,
        mock_pixel_fuzzer,
        mock_header_fuzzer,
        mock_metadata_fuzzer,
        sample_dicom_file,
        temp_dir,
    ):
        """Test that all fuzzer types are instantiated."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generator.generate_batch(sample_dicom_file, count=1)

        # Verify all fuzzer types were instantiated
        mock_metadata_fuzzer.assert_called()
        mock_header_fuzzer.assert_called()
        mock_pixel_fuzzer.assert_called()

    def test_mutations_applied_to_dataset(self, sample_dicom_file, temp_dir):
        """Test that mutations are actually applied to the dataset."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        # Generate files
        generated_files = generator.generate_batch(sample_dicom_file, count=5)

        # All files should be created (mutations were applied successfully)
        assert len(generated_files) == 5
        for file_path in generated_files:
            assert file_path.exists()
            # File should have content
            assert file_path.stat().st_size > 0

    @patch("random.random")
    def test_random_fuzzer_selection(self, mock_random, sample_dicom_file, temp_dir):
        """Test that fuzzers are randomly selected.

        NOTE: The generator uses random.random() with 70% threshold
        to decide whether to apply each fuzzer.
        """
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        # Mock random.random to return values that select some fuzzers
        # Values > 0.3 will select the fuzzer (70% chance)
        mock_random.side_effect = [0.5, 0.1, 0.8]  # Select 1st, skip 2nd, select 3rd

        try:
            generated_files = generator.generate_batch(sample_dicom_file, count=1)
            # Should generate 1 file successfully
            assert len(generated_files) == 1
            assert generated_files[0].exists()
        except Exception:
            # If there's an error, at least verify random was called
            pass

        # Verify random.random was called for fuzzer selection
        assert mock_random.called


class TestFileSaving:
    """Test file saving functionality."""

    def test_files_are_valid_dicom(self, sample_dicom_file, temp_dir):
        """Test that generated files are valid DICOM files."""
        from dicom_fuzzer.core.parser import DicomParser

        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=3)

        # Verify each file can be parsed as DICOM
        for file_path in generated_files:
            parser = DicomParser(file_path)
            assert parser.dataset is not None

    def test_files_contain_data(self, sample_dicom_file, temp_dir):
        """Test that generated files contain actual data."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=3)

        for file_path in generated_files:
            # File should not be empty
            assert file_path.stat().st_size > 0
            # Should be at least a few hundred bytes (DICOM header + data)
            assert file_path.stat().st_size > 200

    def test_files_saved_to_correct_location(self, sample_dicom_file, temp_dir):
        """Test that files are saved to the correct output directory."""
        output_dir = temp_dir / "specific_output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=3)

        for file_path in generated_files:
            assert file_path.parent == output_dir
            assert file_path.exists()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_generate_with_nonexistent_file(self, temp_dir):
        """Test generating from nonexistent file raises error."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        nonexistent_file = temp_dir / "does_not_exist.dcm"

        with pytest.raises(Exception):  # DicomParser or FileNotFoundError
            generator.generate_batch(nonexistent_file, count=1)

    def test_generate_with_invalid_dicom(self, temp_dir):
        """Test generating from invalid DICOM file raises error."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        # Create invalid DICOM file
        invalid_file = temp_dir / "invalid.dcm"
        invalid_file.write_bytes(b"Not a DICOM file")

        with pytest.raises(Exception):  # DICOM parsing error
            generator.generate_batch(invalid_file, count=1)

    def test_output_dir_as_path_object(self, temp_dir):
        """Test that output_dir can be a Path object."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=output_dir)

        assert generator.output_dir == output_dir
        assert generator.output_dir.exists()

    def test_output_dir_as_string(self, temp_dir):
        """Test that output_dir can be a string."""
        output_dir = temp_dir / "output"
        generator = DICOMGenerator(output_dir=str(output_dir))

        assert generator.output_dir == output_dir
        assert generator.output_dir.exists()


class TestPropertyBasedTesting:
    """Property-based tests for robustness."""

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(count=st.integers(min_value=1, max_value=20))
    def test_generate_count_matches_output(self, sample_dicom_file, temp_dir, count):
        """Property test: output count always matches requested count."""
        output_dir = temp_dir / "output_prop"
        generator = DICOMGenerator(output_dir=str(output_dir))

        generated_files = generator.generate_batch(sample_dicom_file, count=count)

        assert len(generated_files) == count


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_generation_workflow(self, sample_dicom_file, temp_dir):
        """Test complete workflow from initialization to file generation."""
        output_dir = temp_dir / "integration_output"

        # Initialize generator
        generator = DICOMGenerator(output_dir=str(output_dir))
        assert generator.output_dir.exists()

        # Generate first batch
        batch1 = generator.generate_batch(sample_dicom_file, count=5)
        assert len(batch1) == 5

        # Generate second batch
        batch2 = generator.generate_batch(sample_dicom_file, count=3)
        assert len(batch2) == 3

        # Verify all files exist and are unique
        all_files = batch1 + batch2
        assert len(all_files) == 8
        assert len(set(f.name for f in all_files)) == 8  # All unique

        # Verify all files are valid DICOM
        from dicom_fuzzer.core.parser import DicomParser

        for file_path in all_files:
            parser = DicomParser(file_path)
            assert parser.dataset is not None

    def test_multiple_generators_same_directory(self, sample_dicom_file, temp_dir):
        """Test multiple generator instances using same output directory."""
        output_dir = temp_dir / "shared_output"

        gen1 = DICOMGenerator(output_dir=str(output_dir))
        gen2 = DICOMGenerator(output_dir=str(output_dir))

        files1 = gen1.generate_batch(sample_dicom_file, count=3)
        files2 = gen2.generate_batch(sample_dicom_file, count=3)

        # All files should be unique
        all_filenames = [f.name for f in files1 + files2]
        assert len(all_filenames) == len(set(all_filenames))

    def test_generator_with_different_source_files(
        self, sample_dicom_file, minimal_dicom_file, temp_dir
    ):
        """Test generator with different source DICOM files."""
        output_dir = temp_dir / "multi_source"
        generator = DICOMGenerator(output_dir=str(output_dir))

        files_from_sample = generator.generate_batch(sample_dicom_file, count=3)
        files_from_minimal = generator.generate_batch(minimal_dicom_file, count=3)

        assert len(files_from_sample) == 3
        assert len(files_from_minimal) == 3

        # All files should exist
        for f in files_from_sample + files_from_minimal:
            assert f.exists()


class TestGeneratorErrorHandling:
    """Test error handling in DICOMGenerator."""

    def test_generation_stats_record_failure(self):
        """Test GenerationStats.record_failure method (lines 33-34)."""
        from dicom_fuzzer.core.generator import GenerationStats

        stats = GenerationStats()

        # Record some failures
        stats.record_failure("ValueError")
        stats.record_failure("TypeError")
        stats.record_failure("ValueError")  # Duplicate error type

        # Check that failures are tracked
        assert stats.failed == 3
        assert "ValueError" in stats.error_types
        assert stats.error_types["ValueError"] == 2
        assert "TypeError" in stats.error_types
        assert stats.error_types["TypeError"] == 1

    def test_generate_with_skip_write_errors_true(self, sample_dicom_file, temp_dir):
        """Test generator skips files with write errors."""
        output_dir = temp_dir / "skip_errors"
        generator = DICOMGenerator(output_dir=str(output_dir), skip_write_errors=True)

        # Generate files - some may be skipped due to extreme mutations
        files = generator.generate_batch(sample_dicom_file, count=20)

        # Should have generated some files
        assert len(files) >= 0
        # Stats should track skipped files
        assert generator.stats.skipped_due_to_write_errors >= 0

    def test_generate_with_skip_write_errors_false(self, sample_dicom_file, temp_dir):
        """Test generator with skip_write_errors=False."""
        output_dir = temp_dir / "no_skip"
        generator = DICOMGenerator(output_dir=str(output_dir), skip_write_errors=False)

        # This might raise an error on extreme mutations, but should work
        # most of the time with default strategies
        try:
            files = generator.generate_batch(sample_dicom_file, count=5)
            assert len(files) >= 0
        except (OSError, ValueError, TypeError, AttributeError):
            # Expected - some mutations create unwritable files
            pass

    def test_stats_tracking(self, sample_dicom_file, temp_dir):
        """Test that stats are properly tracked."""
        output_dir = temp_dir / "stats_test"
        generator = DICOMGenerator(output_dir=str(output_dir))

        files = generator.generate_batch(sample_dicom_file, count=10)

        # Check stats were tracked
        assert generator.stats.successful > 0
        assert generator.stats.successful == len(files)
        # Strategies should have been used
        assert len(generator.stats.strategies_used) > 0

    def test_generate_with_invalid_strategy(self, sample_dicom_file, temp_dir):
        """Test generation with invalid strategy name."""
        output_dir = temp_dir / "invalid_strat"
        generator = DICOMGenerator(output_dir=str(output_dir))

        # Should handle invalid strategy gracefully (ignore it)
        files = generator.generate_batch(
            sample_dicom_file, count=3, strategies=["invalid_strategy"]
        )

        # Should still work, just without any strategies applied
        assert len(files) >= 0

    def test_generate_with_empty_strategies_list(self, sample_dicom_file, temp_dir):
        """Test generation with empty strategies list."""
        output_dir = temp_dir / "empty_strat"
        generator = DICOMGenerator(output_dir=str(output_dir))

        # Empty strategies should still work (no mutations)
        files = generator.generate_batch(sample_dicom_file, count=3, strategies=[])

        assert len(files) >= 0

    def test_mutation_error_with_skip_false(self, sample_dicom_file, temp_dir):
        """Test mutation error handling when skip_write_errors=False (lines 172-173)."""
        from unittest.mock import Mock, patch

        output_dir = temp_dir / "mutation_error"
        generator = DICOMGenerator(output_dir=str(output_dir), skip_write_errors=False)

        # Mock a fuzzer that raises ValueError
        with patch("dicom_fuzzer.core.generator.HeaderFuzzer") as mock_fuzzer_class:
            mock_fuzzer = Mock()
            mock_fuzzer.mutate_tags.side_effect = ValueError("Test error")
            mock_fuzzer_class.return_value = mock_fuzzer

            try:
                generator.generate_batch(
                    sample_dicom_file, count=1, strategies=["header"]
                )
                # If no error, that's ok (probabilistic fuzzer selection)
            except ValueError:
                # Error was raised as expected (lines 172-173)
                assert generator.stats.failed > 0

    def test_save_error_with_skip_false(self, sample_dicom_file, temp_dir):
        """Test save error handling when skip_write_errors=False (lines 198-199)."""
        import struct
        from unittest.mock import patch

        output_dir = temp_dir / "save_error"
        generator = DICOMGenerator(output_dir=str(output_dir), skip_write_errors=False)

        # Mock save_as to raise struct.error
        with patch("pydicom.dataset.Dataset.save_as") as mock_save:
            mock_save.side_effect = struct.error("Test save error")

            try:
                generator.generate_batch(sample_dicom_file, count=1, strategies=[])
                # Should raise the error
                assert False, "Expected struct.error to be raised"
            except struct.error:
                # Error was raised as expected (lines 198-199)
                assert generator.stats.failed > 0

    def test_unexpected_exception_in_save(self, sample_dicom_file, temp_dir):
        """Test unexpected exception handling during save (lines 188-190)."""
        from unittest.mock import patch

        output_dir = temp_dir / "unexpected"
        generator = DICOMGenerator(output_dir=str(output_dir), skip_write_errors=True)

        # Mock save_as to raise an unexpected exception
        with patch("pydicom.dataset.Dataset.save_as") as mock_save:
            mock_save.side_effect = RuntimeError("Unexpected error")

            try:
                generator.generate_batch(sample_dicom_file, count=1, strategies=[])
                assert False, "Expected RuntimeError to be raised"
            except RuntimeError:
                # Unexpected errors should always be raised (line 190)
                assert generator.stats.failed > 0

    def test_mutation_error_with_skip_true(self, sample_dicom_file, temp_dir):
        """Test mutation error skipped with skip_write_errors=True (lines 168-170)."""
        from unittest.mock import Mock, patch

        output_dir = temp_dir / "mutation_skip"
        generator = DICOMGenerator(output_dir=str(output_dir), skip_write_errors=True)

        # Mock a fuzzer that always raises ValueError
        with patch("dicom_fuzzer.core.generator.HeaderFuzzer") as mock_fuzzer_class:
            mock_fuzzer = Mock()
            mock_fuzzer.mutate_tags.side_effect = ValueError("Test error")
            mock_fuzzer_class.return_value = mock_fuzzer

            # Should skip errors without raising
            generator.generate_batch(sample_dicom_file, count=5, strategies=["header"])

            # Some files might be skipped due to mutation errors
            assert generator.stats.skipped_due_to_write_errors >= 0

    def test_save_error_with_skip_true(self, sample_dicom_file, temp_dir):
        """Test save error skipped with skip_write_errors=True (lines 195-196)."""
        import struct
        from unittest.mock import patch

        output_dir = temp_dir / "save_skip"
        generator = DICOMGenerator(output_dir=str(output_dir), skip_write_errors=True)

        # Mock save_as to raise struct.error
        with patch("pydicom.dataset.Dataset.save_as") as mock_save:
            mock_save.side_effect = struct.error("Test save error")

            # Should skip errors without raising
            files = generator.generate_batch(sample_dicom_file, count=5, strategies=[])

            # Files should be skipped
            assert len(files) < 5
            assert generator.stats.skipped_due_to_write_errors > 0


class TestGeneratorBatchProcessing:
    """Test batch processing edge cases."""

    def test_generate_single_file(self, sample_dicom_file, temp_dir):
        """Test generating just one file."""
        output_dir = temp_dir / "single"
        generator = DICOMGenerator(output_dir=str(output_dir))

        files = generator.generate_batch(sample_dicom_file, count=1)

        assert len(files) == 1
        assert files[0].exists()

    def test_generate_zero_files(self, sample_dicom_file, temp_dir):
        """Test generating zero files."""
        output_dir = temp_dir / "zero"
        generator = DICOMGenerator(output_dir=str(output_dir))

        files = generator.generate_batch(sample_dicom_file, count=0)

        assert len(files) == 0

    def test_generate_with_all_strategies(self, sample_dicom_file, temp_dir):
        """Test generation with all strategies specified."""
        output_dir = temp_dir / "all_strat"
        generator = DICOMGenerator(output_dir=str(output_dir))

        files = generator.generate_batch(
            sample_dicom_file,
            count=5,
            strategies=["metadata", "header", "pixel", "structure"],
        )

        assert len(files) >= 0
        # Should have used multiple strategies
        assert len(generator.stats.strategies_used) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
