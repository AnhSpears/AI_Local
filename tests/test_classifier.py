import os
from core.classifier import SimpleClassifier


def test_classifier_train_and_predict(tmp_path):
    texts = ["Giới thiệu AI và agent", "Học lập trình Python cơ bản", "Tạo nội dung video cho Youtube"]
    labels = ["ai", "programming", "content_creation"]

    clf = SimpleClassifier()
    clf.train(texts, labels, save=False)

    label, conf = clf.predict("Học cách viết code Python để xử lý dữ liệu")
    assert label in {"programming", "ai", "other"}  # allow small ambiguity
    assert 0.0 <= conf <= 1.0
