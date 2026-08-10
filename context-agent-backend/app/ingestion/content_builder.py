from app.schemas.article import NormalizedArticleDTO


def build_cleaned_text(article: NormalizedArticleDTO) -> str:
    parts: list[str] = [article.title.strip()]
    if article.summary:
        parts.append(article.summary.strip())
    if article.body and article.body.strip() and article.body.strip() != (article.summary or "").strip():
        parts.append(article.body.strip())
    return "\n\n".join(part for part in parts if part)
