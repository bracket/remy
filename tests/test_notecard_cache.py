from pathlib import Path
import pytest

from remy.exceptions import RemyError

FILE = Path(__file__).absolute()
HERE = FILE.parent
TEST_NOTES = HERE / 'data/test_notes'


def test_notecard_cache():
    from remy.notecard_cache import NotecardCache

    cache = NotecardCache(TEST_NOTES)
    card = cache.find_card_by_label('weasel')

    assert card is not None
    assert card.primary_label == '1'


def test_field_indices_valid_fields():
    """Test that field_indices returns indices for valid field names."""
    from remy.notecard_cache import NotecardCache

    cache = NotecardCache(TEST_NOTES)
    
    # Request valid fields from config
    indices = cache.field_indices(['TAG', 'STATUS', 'PRIORITY'])
    
    assert 'TAG' in indices
    assert 'STATUS' in indices
    assert 'PRIORITY' in indices
    assert len(indices) == 3


def test_field_indices_case_insensitive():
    """Test that field_indices is case-insensitive."""
    from remy.notecard_cache import NotecardCache

    cache = NotecardCache(TEST_NOTES)
    
    # Request fields with mixed case
    indices = cache.field_indices(['tag', 'Status', 'PRIORITY'])
    
    # Should be uppercased in the result
    assert 'TAG' in indices
    assert 'STATUS' in indices
    assert 'PRIORITY' in indices


def test_field_indices_unknown_field_raises_error():
    """Test that requesting an unknown field raises RemyError."""
    from remy.notecard_cache import NotecardCache

    cache = NotecardCache(TEST_NOTES)
    
    # Request a non-existent field
    with pytest.raises(RemyError) as exc_info:
        cache.field_indices(['UNKNOWN_FIELD'])
    
    # Error message should list available fields
    assert 'Unknown field index: UNKNOWN_FIELD' in str(exc_info.value)
    assert 'Available field indices:' in str(exc_info.value)
    assert 'TAG' in str(exc_info.value)


def test_field_indices_typo_in_field_raises_error():
    """Test that a typo in a field name raises a helpful error."""
    from remy.notecard_cache import NotecardCache

    cache = NotecardCache(TEST_NOTES)
    
    # Common typo: STATSU instead of STATUS
    with pytest.raises(RemyError) as exc_info:
        cache.field_indices(['STATSU'])
    
    assert 'Unknown field index: STATSU' in str(exc_info.value)
    assert 'Available field indices:' in str(exc_info.value)
    assert 'STATUS' in str(exc_info.value)


def test_field_indices_valid_pseudo_index():
    """Test that valid pseudo-indices are synthesized correctly."""
    from remy.notecard_cache import NotecardCache

    cache = NotecardCache(TEST_NOTES)
    
    # Request valid pseudo-indices
    indices = cache.field_indices(['@ID', '@LABEL', '@PRIMARY-LABEL'])
    
    assert '@ID' in indices
    assert '@LABEL' in indices
    assert '@PRIMARY-LABEL' in indices
    
    # Verify they are PseudoIndex instances
    from remy.notecard_index import PseudoIndex
    assert isinstance(indices['@ID'], PseudoIndex)
    assert isinstance(indices['@LABEL'], PseudoIndex)
    assert isinstance(indices['@PRIMARY-LABEL'], PseudoIndex)


def test_field_indices_invalid_pseudo_index_raises_error():
    """Test that requesting an unknown pseudo-index raises RemyError."""
    from remy.notecard_cache import NotecardCache

    cache = NotecardCache(TEST_NOTES)
    
    # Request a non-existent pseudo-index
    with pytest.raises(RemyError) as exc_info:
        cache.field_indices(['@UNKNOWN'])
    
    # Error message should list available pseudo-indices
    assert 'Unknown pseudo-index: @UNKNOWN' in str(exc_info.value)
    assert 'Known pseudo-indices:' in str(exc_info.value)
    assert '@ID' in str(exc_info.value)
    assert '@LABEL' in str(exc_info.value)
    assert '@PRIMARY-LABEL' in str(exc_info.value)


def test_field_indices_mixed_valid_and_pseudo():
    """Test that field_indices handles both real fields and pseudo-indices."""
    from remy.notecard_cache import NotecardCache
    from remy.notecard_index import NotecardIndex, PseudoIndex

    cache = NotecardCache(TEST_NOTES)
    
    # Request mix of real fields and pseudo-indices
    indices = cache.field_indices(['TAG', '@ID', 'STATUS', '@LABEL'])
    
    assert len(indices) == 4
    assert isinstance(indices['TAG'], NotecardIndex)
    assert isinstance(indices['@ID'], PseudoIndex)
    assert isinstance(indices['STATUS'], NotecardIndex)
    assert isinstance(indices['@LABEL'], PseudoIndex)


def test_field_indices_pseudo_index_case_insensitive():
    """Test that pseudo-indices are case-insensitive."""
    from remy.notecard_cache import NotecardCache

    cache = NotecardCache(TEST_NOTES)
    
    # Request pseudo-indices with different cases
    indices = cache.field_indices(['@id', '@Label', '@PRIMARY-LABEL'])
    
    # Should be uppercased in the result
    assert '@ID' in indices
    assert '@LABEL' in indices
    assert '@PRIMARY-LABEL' in indices

