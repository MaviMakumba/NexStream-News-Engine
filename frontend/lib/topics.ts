// ÜRETİLDİ — ELLE DÜZENLEME. Kaynak: src/domain/topics.py
// Yeniden üret: python scripts/gen_frontend_topics.py (tests/infrastructure/test_frontend_topics_sync.py kaymayı yakalar)
export const TOPICS = [
  { id: "Technology", labels: {"TR": "Teknoloji", "EN": "Technology"} },
  { id: "Sports", labels: {"TR": "Spor", "EN": "Sports"} },
  { id: "Economy", labels: {"TR": "Ekonomi", "EN": "Economy"} },
  { id: "Politics", labels: {"TR": "Siyaset", "EN": "Politics"} },
  { id: "Health", labels: {"TR": "Sağlık", "EN": "Health"} },
  { id: "Culture", labels: {"TR": "Kültür", "EN": "Culture"} },
  { id: "World", labels: {"TR": "Dünya", "EN": "World"} },
  { id: "Science", labels: {"TR": "Bilim", "EN": "Science"} },
  { id: "Crypto", labels: {"TR": "Kripto", "EN": "Crypto"} },
  { id: "Environment", labels: {"TR": "Çevre & İklim", "EN": "Environment & Climate"} },
  { id: "Entertainment", labels: {"TR": "Eğlence", "EN": "Entertainment"} },
  { id: "Other", labels: {"TR": "Diğer", "EN": "Other"} },
] as const;

export type TopicId = (typeof TOPICS)[number]["id"];
