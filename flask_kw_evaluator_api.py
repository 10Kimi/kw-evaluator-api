from flask import Flask, request, jsonify, send_file
import pandas as pd
import re
import io

app = Flask(__name__)

NEGATIVE_WORDS = [
    "やめとけ", "やめ とけ", "意味ない", "意味 ない", "後悔", "失敗", "デメリット",
    "辛い", "つらい", "できない", "無理", "不利", "ゴキブリ", "死亡", "最悪", "ブラック",
    "いじめ", "怖い", "辞めたい", "やめたい", "嫌い", "嫌", "不満", "疲れた", "難しい"
]

def is_negative_kw(keyword):
    normalized = re.sub(r'\s+', '', str(keyword).lower())
    return any(neg in normalized for neg in NEGATIVE_WORDS)

def detailed_weak_media_score(row):
    score = 0
    for col, rank_col in [
        ("Q&Aサイト", "Unnamed: 8"),
        ("無料ブログ", "Unnamed: 10"),
        ("TikTok", "Unnamed: 12"),
        ("Instagram", "Unnamed: 14"),
        ("エックス", "Unnamed: 16"),
        ("Facebook", "Unnamed: 18")
    ]:
        rank = row.get(rank_col)
        if pd.notnull(rank):
            try:
                rank = int(rank)
                if rank == 1:
                    score += 25
                elif rank == 2:
                    score += 20
                elif rank == 3:
                    score += 15
                elif rank == 4:
                    score += 10
                elif rank == 5:
                    score += 9
                elif rank == 6:
                    score += 8
                elif rank == 7:
                    score += 7
                elif 8 <= rank <= 10:
                    score += 5
            except:
                continue
    return score

@app.route('/evaluate', methods=['POST'])
def evaluate_keywords():
    if 'file' not in request.files:
        return "No file part in the request", 400

    file = request.files['file']
    df = pd.read_csv(file)

    def estimate_kd(row):
        if not pd.isna(row.get("SEO難易度")):
            return row.get("SEO難易度")
        try:
            return round(float(row["allintitle"]) / float(row["月間検索数"]) * 100, 2)
        except:
            return None

    df["仮KD"] = df.apply(estimate_kd, axis=1)
    df["媒体補正点"] = df.apply(detailed_weak_media_score, axis=1)
    df["ネガティブKW"] = df["キーワード"].apply(is_negative_kw)

    def calculate_kdp_score(row):
        score = 0
        try:
            search_score = min(float(row["月間検索数"]) / 200 * 30, 30)
            score += search_score
        except:
            pass
        try:
            cpc_score = min(float(row["CPC($)"]) / 5 * 20, 20)
            score += cpc_score
        except:
            pass
        try:
            comp_score = max(0, 20 - float(row["競合性"]) / 5)
            score += comp_score
        except:
            pass
        score += row["媒体補正点"]
        return round(score, 2)

    df["KDPスコア"] = df.apply(calculate_kdp_score, axis=1)

    # 出力
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='evaluated_keywords.csv'
    )

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
