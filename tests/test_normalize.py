from rulecheck_ar.normalize import normalize_ar


def test_removes_diacritics_and_tatweel():
    assert normalize_ar("لَا أَسْتَطِيعُ") == normalize_ar("لا استطيع")
    assert normalize_ar("مســاعدة") == normalize_ar("مساعدة")


def test_unifies_letter_variants():
    assert normalize_ar("إلى آخره") == normalize_ar("الي اخره")
    assert normalize_ar("مدرسة") == normalize_ar("مدرسه")


def test_collapses_whitespace_and_lowercases():
    assert normalize_ar("  I   CAN'T \n help ") == "i can't help"


def test_curly_apostrophe_is_unified():
    assert normalize_ar("I can’t") == "i can't"
