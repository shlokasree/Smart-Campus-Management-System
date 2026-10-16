from sklearn.feature_extraction.text import HashingVectorizer


# Always produces exactly 128 dimensions
vectorizer = HashingVectorizer(
    n_features=128,
    alternate_sign=False,
    norm="l2",
    stop_words="english"
)


def create_embedding(text):
    """
    Convert complaint text into a consistent 128-dimensional vector.
    """
    if not text or not text.strip():
        return [0.0] * 128

    matrix = vectorizer.transform([text])

    vector = matrix.toarray()[0]

    return vector.astype(float).tolist()