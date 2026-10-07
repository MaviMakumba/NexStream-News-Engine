from src.adapters.scrapers.article_extractor import extract_article_text

BODY_1 = "Kulüp doktoru oyuncunun sağ ayak bileğindeki sakatlığın ciddi olduğunu açıkladı."
BODY_2 = "Yıldız oyuncunun yaklaşık üç hafta sahalardan uzak kalması bekleniyor, tedavi sürüyor."


def test_extracts_article_paragraphs_and_drops_nav_script_footer():
    html = f"""<html><head><meta charset="utf-8"><title>x</title><script>var a = 1;</script></head>
    <body><nav><p>Anasayfa Spor Ekonomi Dünya Magazin Gündem Yaşam</p></nav>
    <article><h1>Başlık</h1><p>{BODY_1}</p><p>{BODY_2}</p></article>
    <footer><p>Tüm hakları saklıdır. Çerez politikası ve gizlilik bildirimi için tıklayın.</p></footer>
    </body></html>"""
    text = extract_article_text(html)
    assert text == f"{BODY_1}\n\n{BODY_2}"


def test_without_article_tag_picks_densest_paragraph_group():
    html = f"""<html><body>
    <div class="story"><p>{BODY_1}</p><p>{BODY_2}</p></div>
    <div class="related"><p>Kısa ilgili haber başlığı bir cümle daha uzun yapıldı şimdi tamam.</p></div>
    </body></html>"""
    text = extract_article_text(html)
    assert BODY_1 in text and BODY_2 in text
    assert "ilgili haber" not in text


def test_article_body_split_across_sibling_containers_is_kept_whole():
    """Birçok şablon gövdeyi reklam alanları etrafında birkaç <div>'e böler; doktor açıklaması
    ikinci div'deyse yalnızca en büyük div'i almak tam bu özelliğin hedef durumunu kaçırırdı."""
    html = f"""<html><body><article>
    <div class="blk"><p>{BODY_1}</p></div>
    <div class="ad"><p>Reklam alanı: şimdi indirin, kaçırmayın, özel fırsatlar sizi bekliyor bugün.</p></div>
    <div class="blk"><p>{BODY_2}</p></div>
    </article></body></html>"""
    text = extract_article_text(html)
    assert BODY_1 in text and BODY_2 in text


def test_picks_the_article_with_the_most_text_not_the_first_one():
    card = "<article><p>Kısa ilgili haber kartı metni, kırk karakterden uzun ama makale değil.</p></article>"
    html = f"<html><body>{card}<article><p>{BODY_1}</p><p>{BODY_2}</p></article></body></html>"
    text = extract_article_text(html)
    assert BODY_1 in text and BODY_2 in text and "ilgili haber kartı" not in text


def test_short_paragraphs_are_ignored():
    html = f"<html><body><article><p>Paylaş</p><p>{BODY_1}</p><p>Yorum yap</p></article></body></html>"
    assert extract_article_text(html) == BODY_1


def test_accepts_bytes_with_turkish_characters():
    html = f'<html><head><meta charset="utf-8"></head><body><article><p>{BODY_1}</p></article></body></html>'
    assert extract_article_text(html.encode("utf-8")) == BODY_1


def test_empty_or_paragraphless_html_returns_empty_string():
    assert extract_article_text("") == ""
    assert extract_article_text("<html><body><div>sadece div</div></body></html>") == ""
