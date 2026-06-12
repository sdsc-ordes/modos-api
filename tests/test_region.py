import pytest
from modos.genomics.region import Region


def test_invalid_region():
    with pytest.raises(ValueError):
        Region(chrom="chr1", start=10, end=5)

    with pytest.raises(ValueError):
        Region(chrom="chr1", start=-10, end=-1)

    with pytest.raises(ValueError):
        Region(chrom="", start=10, end=11)


def test_overlap():
    region1 = Region(chrom="chr1", start=10, end=20)
    region2 = Region(chrom="chr1", start=15, end=25)
    region3 = Region(chrom="chr1", start=150, end=250)
    assert region2.overlaps(region1)
    assert region1.overlaps(region2)
    assert not region3.overlaps(region1)


def test_overlap_contained_region():
    """A region fully contained in another overlaps it, both ways."""
    outer = Region(chrom="chr1", start=10, end=100)
    inner = Region(chrom="chr1", start=40, end=50)
    assert outer.overlaps(inner)
    assert inner.overlaps(outer)


def test_contain():
    region1 = Region(chrom="chr1", start=10, end=20)
    region2 = Region(chrom="chr1", start=15, end=18)
    assert region1.contains(region2)
    assert not region2.contains(region1)
