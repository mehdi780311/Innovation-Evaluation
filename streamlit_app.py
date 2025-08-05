# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import asyncio
import httpx  # For making asynchronous HTTP requests
import json

# -----------------------------------------------------------------------------
# تنظیمات صفحه
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="داشبورد تحلیل با Gemini 2.5 Flash")

# -----------------------------------------------------------------------------
# تعریف شاخص‌های ارزیابی
# -----------------------------------------------------------------------------
ANALYSIS_CRITERIA = {
    "حوزه علمی": {
        "labels": ["پزشکی بالینی", "دندانپزشکی", "داروسازی", "علوم پایه پزشکی", "بهداشت و اپیدمیولوژی", "پرستاری و مامایی", "توانبخشی و پیراپزشکی"],
    },
    "فناوری یا نوآوری خاص": {
        "labels": ["هوش مصنوعی در پزشکی", "مهندسی بافت و سلول‌های بنیادی", "تجهیزات پزشکی پیشرفته", "پزشکی از راه دور (Telemedicine)", "ژن‌درمانی و پزشکی شخصی‌سازی‌شده", "نانوتکنولوژی دارویی", "بدون نوآوری خاص"],
    },
    "حل مسئله صنعتی/اجتماعی": {
        "labels": ["تشخیص و درمان بیماری‌ها", "توسعه داروها و واکسن‌ها", "ارتقاء سلامت عمومی", "بهبود مدیریت نظام سلامت", "نوآوری در تجهیزات پزشکی", "فاقد مسئله مشخص"],
    },
    "قابلیت تجاری‌سازی": {
        "labels": ["پتانسیل بالا", "پتانسیل متوسط", "پتانسیل کم"],
    },
    "همکاری با صنعت/نهاد غیردانشگاهی": {
        "labels": ["دارای همکاری", "بدون همکاری"],
    }
}

# -----------------------------------------------------------------------------
# توابع اصلی برای پردازش و تحلیل با Gemini
# -----------------------------------------------------------------------------

async def call_gemini_api(prompt, api_key):
    """
    یک فراخوانی API ناهمزمان به مدل Gemini با استفاده از کلید API کاربر ارسال می‌کند.
    """
    if not api_key:
        st.error("کلید API گوگل وارد نشده است. لطفاً کلید خود را برای ادامه وارد کنید.")
        return None
        
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "topP": 0.95,
            "maxOutputTokens": 50,
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if (result.get('candidates') and 
                result['candidates'][0].get('content') and 
                result['candidates'][0]['content'].get('parts')):
                
                text_response = result['candidates'][0]['content']['parts'][0].get('text', '').strip()
                return text_response
            else:
                error_info = result.get('promptFeedback', 'جزئیات موجود نیست.')
                st.warning(f"پاسخ مورد انتظار از مدل دریافت نشد. دلیل: {error_info}")
                return None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                st.error("خطای 403: دسترسی ممنوع. لطفاً از معتبر بودن و فعال بودن کلید API گوگل خود اطمینان حاصل کنید.")
            elif e.response.status_code == 400:
                 st.error(f"خطای 400: درخواست نامعتبر. ممکن است مشکل از فرمت درخواست یا کلید API باشد. جزئیات: {e.response.text}")
            else:
                st.error(f"خطا در ارتباط با سرور Gemini: {e}")
            return None
        except httpx.RequestError as e:
            st.error(f"خطا در برقراری ارتباط با سرویس Gemini: {e}")
            return None
        except Exception as e:
            st.error(f"خطای غیرمنتظره در هنگام فراخوانی API: {e}")
            return None


async def analyze_text_with_gemini(text, criterion_name, labels, default_label, api_key):
    """
    متن را با استفاده از مدل Gemini و یک پرامپت ساختاریافته تحلیل می‌کند.
    """
    prompt = f"""
    You are an expert assistant specializing in analyzing scientific texts.
    Analyze the following Persian thesis text based on the criterion: "{criterion_name}".
    Choose the single best-fitting category from this list:
    [{', '.join(labels)}]

    Output ONLY the category name in Persian and nothing else.

    Thesis text:
    ---
    {text}
    ---
    """
    
    response_text = await call_gemini_api(prompt, api_key)
    
    if response_text:
        cleaned_response = response_text.replace("*", "").replace("\"", "").strip()
        if cleaned_response in labels:
            return cleaned_response
    
    return default_label


async def process_theses_async(df, api_key):
    """
    دیتافریم ورودی را به صورت ناهمزمان با Gemini پردازش کرده و نتایج تحلیل را برمی‌گرداند.
    """
    results = []
    progress_bar = st.progress(0, text="در حال آماده‌سازی برای تحلیل...")
    total_rows = len(df)
    
    for index, row in df.iterrows():
        title = str(row.get("عنوان", ""))
        abstract = str(row.get("چکیده", ""))
        
        if not title or not abstract:
            continue
            
        full_text = f"عنوان: {title}\nچکیده: {abstract}"
        analysis_result = {"عنوان": title}
        
        tasks = []
        for criterion, data in ANALYSIS_CRITERIA.items():
            default_label = "نامشخص"
            if criterion == "فناوری یا نوآوری خاص": default_label = "بدون نوآوری خاص"
            elif criterion == "حل مسئله صنعتی/اجتماعی": default_label = "فاقد مسئله مشخص"
            elif criterion == "قابلیت تجاری‌سازی": default_label = "پتانسیل کم"
            elif criterion == "همکاری با صنعت/نهاد غیردانشگاهی": default_label = "بدون همکاری"
            
            task = analyze_text_with_gemini(full_text, criterion, data["labels"], default_label, api_key)
            tasks.append(task)
        
        analyzed_labels = await asyncio.gather(*tasks)
        
        for i, criterion in enumerate(ANALYSIS_CRITERIA.keys()):
            analysis_result[criterion] = analyzed_labels[i]
            
        results.append(analysis_result)
        
        progress_text = f"در حال تحلیل پایان‌نامه {index + 1} از {total_rows}..."
        progress_bar.progress((index + 1) / total_rows, text=progress_text)

    progress_bar.empty()
    return pd.DataFrame(results)

# -----------------------------------------------------------------------------
# رابط کاربری داشبورد (Streamlit UI)
# -----------------------------------------------------------------------------

st.title("♊️ داشبورد تحلیل پایان‌نامه‌ها با Gemini (2.5 Flash)")
st.markdown("""
این ابزار با استفاده از سرویس **Google AI (Gemini)**، پتانسیل پایان‌نامه‌های حوزه علوم پزشکی را ارزیابی می‌کند.
""")

st.info("**مهم:** برای استفاده از این ابزار، به یک کلید API از **Google AI Studio** نیاز دارید.")

api_key = st.text_input("🔑 لطفاً کلید API گوگل (Google AI API Key) خود را اینجا وارد کنید:", type="password", help="کلید خود را می‌توانید به صورت رایگان از Google AI Studio دریافت کنید.")

uploaded_file = st.file_uploader("فایل اکسل خود را اینجا بارگذاری کنید", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)

        if "عنوان" not in df.columns or "چکیده" not in df.columns:
            st.error("خطا: فایل اکسل باید حتماً شامل ستون‌های 'عنوان' و 'چکیده' باشد.")
        else:
            st.success(f"فایل با موفقیت بارگذاری شد. **{len(df)}** پایان‌نامه برای تحلیل شناسایی شد.")
            st.markdown("### پیش‌نمایش داده‌های ورودی")
            st.dataframe(df.head())

            if st.button("شروع تحلیل با Gemini", type="primary", use_container_width=True, disabled=not api_key):
                with st.spinner("لطفاً صبر کنید... در حال ارتباط با سرورهای Gemini و تحلیل داده‌ها..."):
                    result_df = asyncio.run(process_theses_async(df, api_key))
                
                st.balloons()
                st.markdown("---")
                st.markdown("### نتایج نهایی تحلیل")
                
                column_order = ["عنوان"] + list(ANALYSIS_CRITERIA.keys())
                result_df = result_df[column_order]

                st.dataframe(result_df)

                csv = result_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 دانلود نتایج در قالب CSV",
                    data=csv,
                    file_name='tahlil_gemini_flash.csv',
                    mime='text/csv',
                    use_container_width=True
                )

    except Exception as e:
        st.error(f"یک خطای غیرمنتظره در پردازش فایل رخ داد: {e}")
else:
    st.info("ابتدا کلید API خود را وارد کرده و سپس فایل اکسل را بارگذاری کنید.")

