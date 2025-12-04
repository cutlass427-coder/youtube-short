import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time

# ページ設定
st.set_page_config(
    page_title="YouTube Shorts AI Assistant",
    page_icon="🎬",
    layout="wide"
)

# タイトル
st.title("🎬 YouTube Shorts 投稿支援 AIアプリ")
st.markdown("動画をアップロードすると、Geminiがタイトル・説明・タグを提案し、壁打ち相談もできます。")

# サイドバー: APIキー設定
with st.sidebar:
    st.header("設定")
    api_key = st.text_input("Gemini API Key", type="password")
    st.markdown("[APIキーの取得はこちら](https://aistudio.google.com/app/apikey)")
    
    st.divider()
    st.markdown("""
    **使い方:**
    1. APIキーを入力
    2. MP4動画をアップロード
    3. 「解析・生成する」をクリック
    4. 結果をコピーしてYouTubeへ
    5. 気に入らない場合はチャットで相談
    """)

# セッション状態の初期化
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

# Geminiの設定関数
def configure_gemini(api_key):
    genai.configure(api_key=api_key)

# 動画アップロード処理
uploaded_file = st.file_uploader("ショート動画(MP4)をアップロード", type=["mp4"])

# メイン処理
if uploaded_file and api_key:
    configure_gemini(api_key)
    
    # 動画プレビュー（カラム分け）
    col1, col2 = st.columns([1, 2])
    with col1:
        st.video(uploaded_file)
    
    with col2:
        st.info("動画がセットされました。解析ボタンを押してください。")
        
        # 解析ボタン
        if st.button("🚀 解析・案を生成する", type="primary"):
            try:
                with st.spinner('動画をGeminiにアップロード中...'):
                    # 一時ファイルとして保存
                    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                    tfile.write(uploaded_file.read())
                    video_path = tfile.name
                    tfile.close()

                    # Geminiへアップロード
                    video_file = genai.upload_file(path=video_path)
                    
                    # 処理待ち
                    while video_file.state.name == "PROCESSING":
                        time.sleep(2)
                        video_file = genai.get_file(video_file.name)

                    if video_file.state.name == "FAILED":
                        st.error("動画の処理に失敗しました。")
                    else:
                        st.session_state.uploaded_file_name = video_file.name
                        
                        # プロンプト作成
                        prompt = """
                        あなたはプロのYouTubeコンサルタントです。
                        アップロードされた動画はYouTubeショート用です。
                        動画の内容を視覚的・聴覚的に深く分析し、バズるための以下の要素を出力してください。
                        
                        出力フォーマット:
                        【タイトル】 (キャッチーで30文字以内)
                        【説明欄】 (ハッシュタグを含めたSEOに強い説明文)
                        【タグ】 (カンマ区切りで10個程度)
                        
                        分析の根拠も少し添えてください。
                        """

                        with st.spinner('AIが動画を見てアイデアを考えています...'):
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            response = model.generate_content([video_file, prompt])
                            st.session_state.analysis_result = response.text
                            
                            # チャット履歴の初期化（コンテキストを含める）
                            st.session_state.chat_history = [
                                {"role": "user", "content": "この動画の分析と提案をお願いします。"},
                                {"role": "model", "content": response.text}
                            ]
                        
                        # 一時ファイル削除
                        os.unlink(video_path)

            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

# 結果表示エリア
if st.session_state.analysis_result:
    st.divider()
    st.header("📝 生成結果")
    
    # 結果を見やすく表示
    st.markdown(st.session_state.analysis_result)
    
    # コピー用エリア（st.codeを使うとワンクリックでコピーできます）
    with st.expander("コピー用テキストエリア", expanded=True):
        st.text_area("全コピー用", value=st.session_state.analysis_result, height=300)

    # 備考欄
    st.divider()
    st.subheader("📌 備考・メモ")
    remarks = st.text_area("投稿日時やリンク、特記事項などをここにメモできます。", height=100)

    # 壁打ち機能
    st.divider()
    st.header("🤖 壁打ち・相談チャット")
    st.markdown("提案された内容が気に入らない場合や、微調整したい場合はここで相談してください。\n(例: 「もっと女子高生向けにして」「タイトルを3案出して」)")

    # チャット履歴の表示
    for message in st.session_state.chat_history:
        if message["role"] != "system": # システムメッセージは隠す場合
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # チャット入力
    if prompt := st.chat_input("AIに指示・相談する..."):
        # ユーザーの入力を表示
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # Geminiへの問い合わせ
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            # 過去の履歴をコンテキストとして渡す
            chat = model.start_chat(history=st.session_state.chat_history)
            
            with st.spinner("考え中..."):
                response = chat.send_message(prompt)
                
            with st.chat_message("model"):
                st.markdown(response.text)
            
            st.session_state.chat_history.append({"role": "model", "content": response.text})
            
        except Exception as e:
            st.error(f"エラー: {e}")

elif not api_key:
    st.warning("サイドバーからGemini APIキーを入力してください。")