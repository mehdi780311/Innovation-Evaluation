import streamlit as st

st.title("داشبورد تحلیل پایان‌نامه‌های علوم پزشکی با Gemini ")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import json
import asyncio
import httpx  # For making asynchronous HTTP requests

# -----------------------------------------------------------------------------
# تنظیمات صفحه
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="داشبورد تحلیل پایان‌نامه‌های علوم پزشکی با Gemini")

# -----------------------------------------------------------------------------
# تعریف شاخص‌های ارزیابی (بدون کلیدواژه)
# -----------------------------------------------------------------------------
# کلیدواژه‌ها حذف شده‌اند چون تحلیل به طور کامل توسط مدل Gemini انجام می‌شود.
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

async def call_gemini_api(prompt):
    """
    یک فراخوانی API ناهمزمان به مدل Gemini ارسال می‌کند.
    """
    # URL برای دسترسی به مدل Gemini Flash بدون نیاز به کلید (طبق دستورالعمل محیط)
    api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key="
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "topP": 0.95,
            "maxOutputTokens": 50,
        }
    }
    
    headers = {'Content-Type': 'application/json'}
    
    # استفاده از httpx برای ارسال درخواست‌های ناهمزمان
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # ارسال درخواست به API
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()  # ایجاد خطا در صورت پاسخ ناموفق (e.g., 4xx or 5xx)
            result = response.json()
            
            # استخراج متن از پاسخ دریافتی
            if (result.get('candidates') and 
                result['candidates'][0].get('content') and 
                result['candidates'][0]['content'].get('parts')):
                
                text_response = result['candidates'][0]['content']['parts'][0].get('text', '').strip()
                return text_response
            else:
                # مدیریت پاسخ‌های نامعتبر یا مسدود شده
                error_info = result.get('promptFeedback', 'جزئیات موجود نیست.')
                st.warning(f"پاسخ مورد انتظار از مدل دریافت نشد. دلیل: {error_info}")
                return None

        except httpx.RequestError as e:
            st.error(f"خطا در برقراری ارتباط با سرویس Gemini: {e}")
            return None
        except Exception as e:
            st.error(f"خطای غیرمنتظره در هنگام فراخوانی API: {e}")
            return None


async def analyze_text_with_gemini(text, criterion_name, labels, default_label):
    """
    متن را با استفاده از مدل Gemini و یک پرامپت ساختاریافته تحلیل می‌کند.
    """
    # ساخت یک پرامپت (دستور) دقیق برای هدایت مدل به سمت پاسخ مطلوب
    prompt = f"""
    شما یک دستیار متخصص در تحلیل متون علمی و پایان‌نامه‌های حوزه علوم پزشکی هستید.
    متن زیر که شامل عنوان و چکیده یک پایان‌نامه است را با دقت تحلیل کنید.
    وظیفه شما این است که بر اساس محتوای متن، مشخص کنید این پایان‌نامه به کدام یک از دسته‌های زیر در شاخص «{criterion_name}» تعلق دارد.

    دسته‌های ممکن:
    - {', '.join(labels)}

    لطفاً فقط و فقط نام دقیق یکی از دسته‌های بالا را به عنوان پاسخ خروجی دهید. هیچ توضیح اضافه‌ای ندهید.

    متن پایان‌نامه:
    ---
    {text}
    ---
    """
    
    response_text = await call_gemini_api(prompt)
    
    # پاک‌سازی و اعتبارسنجی پاسخ برای اطمینان از تطابق با دسته‌های موجود
    if response_text:
        cleaned_response = response_text.replace("*", "").strip()
        if cleaned_response in labels:
            return cleaned_response
    
    return default_label


async def process_theses_async(df):
    """
    دیتافریم ورودی را به صورت ناهمزمان پردازش کرده و نتایج تحلیل را برمی‌گرداند.
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
        
        # ایجاد تسک‌های ناهمزمان برای هر شاخص از یک پایان‌نامه
        tasks = []
        for criterion, data in ANALYSIS_CRITERIA.items():
            default_label = "نامشخص"
            if criterion == "فناوری یا نوآوری خاص": default_label = "بدون نوآوری خاص"
            elif criterion == "حل مسئله صنعتی/اجتماعی": default_label = "فاقد مسئله مشخص"
            elif criterion == "قابلیت تجاری‌سازی": default_label = "پتانسیل کم"
            elif criterion == "همکاری با صنعت/نهاد غیردانشگاهی": default_label = "بدون همکاری"
            
            task = analyze_text_with_gemini(full_text, criterion, data["labels"], default_label)
            tasks.append(task)
        
        # اجرای همزمان تسک‌ها برای یک پایان‌نامه و جمع‌آوری نتایج
        analyzed_labels = await asyncio.gather(*tasks)
        
        for i, criterion in enumerate(ANALYSIS_CRITERIA.keys()):
            analysis_result[criterion] = analyzed_labels[i]
            
        results.append(analysis_result)
        
        # به‌روزرسانی نوار پیشرفت
        progress_text = f"در حال تحلیل پایان‌نامه {index + 1} از {total_rows}..."
        progress_bar.progress((index + 1) / total_rows, text=progress_text)

    progress_bar.empty()
    return pd.DataFrame(results)

# -----------------------------------------------------------------------------
# رابط کاربری داشبورد (Streamlit UI)
# -----------------------------------------------------------------------------

st.title("♊️ داشبورد تحلیل پایان‌نامه‌های علوم پزشکی با Gemini")
st.markdown("""
این ابزار با استفاده از مدل هوش مصنوعی **Gemini 2.5 Flash**، پتانسیل پایان‌نامه‌های حوزه علوم پزشکی را بر اساس شاخص‌های تخصصی ارزیابی می‌کند.

**راهنما:**
1.  یک فایل اکسل (`.xlsx` یا `.xls`) شامل ستون‌های **`عنوان`** و **`چکیده`** آماده کنید.
2.  فایل را از طریق دکمه زیر بارگذاری کرده و روی دکمه تحلیل کلیک کنید.
""")

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

            if st.button("🔬 شروع تحلیل با Gemini", type="primary", use_container_width=True):
                with st.spinner("لطفاً صبر کنید... در حال ارتباط با سرورهای Gemini و تحلیل داده‌ها... این فرآیند ممکن است زمان‌بر باشد."):
                    # اجرای تابع ناهمزمان اصلی
                    result_df = asyncio.run(process_theses_async(df))
                
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
                    file_name='tahlil_gemini_olom_pezeshki.csv',
                    mime='text/csv',
                    use_container_width=True
                )

    except Exception as e:
        st.error(f"یک خطای غیرمنتظره در پردازش فایل رخ داد: {e}")
else:
    st.info("منتظر بارگذاری فایل اکسل شما هستیم...")
