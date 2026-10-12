from ssr.collect import (
    PR_SUBJECT_RE,
    TEST_PATH_RE,
    BotFilter,
    Identities,
    bus_factor,
    institution_domain,
    is_vendored,
    normalize_version,
    parse_github,
)


def test_bus_factor():
    assert bus_factor([], 0.5) is None
    assert bus_factor([10], 0.5) == 1
    assert bus_factor([6, 2, 2], 0.5) == 1
    assert bus_factor([4, 3, 3], 0.5) == 2
    assert bus_factor([1] * 10, 0.8) == 8


def test_institution_domain():
    generic = {"gmail.com"}
    assert institution_domain("a@physics.umanitoba.ca", generic) == "umanitoba.ca"
    assert institution_domain("a@bnl.gov", generic) == "bnl.gov"
    assert institution_domain("a@cs.ox.ac.uk", generic) == "ox.ac.uk"
    assert institution_domain("a@gmail.com", generic) is None
    assert institution_domain("123+x@users.noreply.github.com", generic) is None
    assert institution_domain("nodomain", generic) is None


def test_identities_merge_by_name_and_email():
    ids = Identities()
    ids.add("Jane Doe", "jane@lab.gov")
    ids.add("Jane Doe", "jane@gmail.com")
    ids.add("jdoe", "jane@gmail.com")
    ids.add("John Roe", "john@lab.gov")
    keys = {ids.key(n, e) for n, e in [("Jane Doe", "jane@lab.gov"), ("jdoe", "jane@gmail.com"), ("Jane Doe", "jane@gmail.com")]}
    assert len(keys) == 1
    assert ids.key("John Roe", "john@lab.gov") not in keys


def test_identities_noreply_login():
    ids = Identities()
    ids.add("J", "123+jdoe@users.noreply.github.com")
    ids.add("Jane", "jdoe@users.noreply.github.com")
    assert ids.key("J", "123+jdoe@users.noreply.github.com") == ids.key("Jane", "jdoe@users.noreply.github.com")


def test_bot_filter():
    f = BotFilter({"bot_patterns": ["[bot]", "pre-commit-ci"], "bot_names": ["copilot"]})
    assert f("dependabot[bot]")
    assert f("Copilot")
    assert f("someone", typename="Bot")
    assert f("pre-commit-ci[bot]")
    assert not f("Claude Dupont")  # only exact names match
    assert not f("Jane Doe", "jane@lab.gov")


def test_pr_subjects_and_paths():
    assert PR_SUBJECT_RE.search("feat: add thing (#123)")
    assert PR_SUBJECT_RE.search("Merge pull request #7 from x/y")
    assert not PR_SUBJECT_RE.search("fix typo")
    assert TEST_PATH_RE.search("src/tests/foo.cc")
    assert TEST_PATH_RE.search("pkg/test_io.py")
    assert TEST_PATH_RE.search("src/algorithms/FooTest.cc")
    assert not TEST_PATH_RE.search("src/algorithms/Foo.cc")


def test_misc():
    assert parse_github("https://github.com/eic/EICrecon") == ("eic", "EICrecon")
    assert parse_github("https://github.com/eic/epic.git") == ("eic", "epic")
    assert parse_github("https://gitlab.com/x/y") is None
    assert is_vendored("cpp/external/CLI/App.hpp")
    assert not is_vendored("src/external.cc")


def test_normalize_version():
    assert normalize_version("v01-38") == normalize_version("1.38") == "1.38"
    assert normalize_version("v1.42.0") == "1.42.0"
    assert normalize_version("v00-17-04") == normalize_version("0.17.4")
    assert normalize_version("2026.03.01") == "2026.3.1"
