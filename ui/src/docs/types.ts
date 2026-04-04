export interface DocArticle {
  id: string;
  slug: string;
  title: string;
  summary: string;
  tags: string[];
  is_ai_created: boolean;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface DocArticleSummary {
  id: string;
  slug: string;
  title: string;
  summary: string;
  tags: string[];
  is_ai_created: boolean;
  created_at: string;
  updated_at: string;
}
