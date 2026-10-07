from src.domain.services.name_verification import correct_names

EVIDENCE = ["Galatasaray Kulüp Doktoru Yener İnce'den Osimhen, Singo, Sallai, Lemina açıklaması. "
            "Osimhen ve Singo ancak testlerden sonra döner, doktor kesin tarih vermedi."]


def test_one_letter_typo_is_corrected_to_the_evidence_spelling():
    text, fixes = correct_names("Doktor Osimren için karar verecek.", EVIDENCE, "Ne zaman döner?")
    assert text == "Doktor Osimhen için karar verecek."
    assert fixes == [("Osimren", "Osimhen")]


def test_two_letter_distance_allowed_for_long_names():
    text, _ = correct_names("Osimiren sakatlandı.", EVIDENCE, "soru")
    assert text == "Osimhen sakatlandı."


def test_turkish_apostrophe_suffix_is_preserved():
    text, _ = correct_names("Osimren'in durumu iyi.", EVIDENCE, "soru")
    assert text == "Osimhen'in durumu iyi."


def test_every_occurrence_is_replaced():
    text, fixes = correct_names("Osimren geliyor. Osimren sahada.", EVIDENCE, "soru")
    assert text == "Osimhen geliyor. Osimhen sahada."
    assert fixes == [("Osimren", "Osimhen")]


def test_correct_spelling_and_unrelated_words_are_untouched():
    answer = "Osimhen ve Singo için Ancak testlerden sonra karar verilecek."
    assert correct_names(answer, EVIDENCE, "soru") == (answer, [])


def test_sentence_initial_common_word_found_lowercase_in_evidence_is_untouched():
    answer = "Ancak doktor kesin tarih vermedi."
    assert correct_names(answer, EVIDENCE, "soru") == (answer, [])


def test_name_spelled_by_the_user_in_the_question_is_respected():
    answer = "Osimren hakkında bilgi yok."
    assert correct_names(answer, EVIDENCE, "Osimren ne zaman döner?") == (answer, [])


def test_ambiguous_nearest_candidates_are_left_alone():
    evidence = ["Sallai ve Sallay aynı haberde geçiyor ama farklı kişiler."]
    answer = "Sallae açıklama yaptı."
    assert correct_names(answer, evidence, "soru") == (answer, [])


def test_short_words_under_five_letters_are_never_touched():
    assert correct_names("Emre geldi.", ["Emir geldi diye yazdı haber."], "soru") == ("Emre geldi.", [])


def test_name_with_no_close_evidence_counterpart_is_untouched():
    answer = "Mertens da konuştu."
    assert correct_names(answer, EVIDENCE, "soru") == (answer, [])


def test_ascii_fied_turkish_i_is_restored_to_the_evidence_spelling():
    evidence = ["İsmail Kahraman bugün açıklama yaptı."]
    text, fixes = correct_names("Ismail Kahraman konuştu.", evidence, "soru")
    assert text == "İsmail Kahraman konuştu."
    assert fixes == [("Ismail", "İsmail")]


def test_same_word_in_different_case_is_not_a_correction():
    evidence = ["Galatasaray kazandı."]
    answer = "GALATASARAY ve galatasaray aynı kulüp."
    assert correct_names(answer, evidence, "soru") == (answer, [])


def test_empty_inputs_are_safe():
    assert correct_names("", EVIDENCE, "soru") == ("", [])
    assert correct_names("Osimren geldi.", [], "soru") == ("Osimren geldi.", [])
