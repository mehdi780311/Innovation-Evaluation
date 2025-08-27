import streamlit as st
import pandas as pd
import google.generativeai as genai
import google.api_core.exceptions  # <-- کتابخانه لازم برای مدیریت خطای محدودیت API
import io
from time import sleep

# --- Page Configuration ---
st.set_page_config(
    page_title="تحلیلگر نوآوری پایان‌نامه",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Functions ---

def create_prompt(title, abstract):
    """
    این تابع یک دستور (prompt) دقیق برای مدل هوش مصنوعی بر اساس جدول ارزیابی نوآوری ایجاد می‌کند.
    """
    return f"""
        شما یک متخصص ارزیابی نوآوری و انتقال فناوری هستید.
        وظیفه شما تحلیل عنوان و چکیده پایان‌نامه زیر بر اساس **"جدول ارزیابی اثبات مفهوم برای رتبه‌بندی نوآوری"** است.
        برای هر یک از ۵ شاخص زیر، یک امتیاز بر اساس توضیحات داده شده اختصاص دهید و در نهایت نمره کل و پتانسیل نوآوری را مشخص کنید.

        **شاخص‌ها و نحوه امتیازدهی:**

        1.  **حوزه علمی پایان‌نامه (امتیاز ۰ تا ۳):** آیا در حوزه‌هایی است که بیشترین ارجحیت را دارند؟ (مانند: داروسازی، مهندسی علوم زیستی، مواد، پزشکی و...). اگر در حوزه‌های با اولویت بالا بود امتیاز ۳، متوسط ۲، کم ۱ و نامرتبط ۰ بدهید.
        2.  **استفاده از فناوری با نوآوری خاص (امتیاز ۰ تا ۳):** آیا چکیده به تکنولوژی نو، مدل فنی، محصول، الگوریتم، فرآیند، یا متدولوژی جدید اشاره دارد؟ اگر اشاره واضحی داشت امتیاز ۳، اشاره ضمنی ۱، و در غیر این صورت ۰ بدهید.
        3.  **حل مسئله صنعتی/اجتماعی مشخص (امتیاز ۰ تا ۳):** آیا در چکیده به یک نیاز یا مسئله کاربردی خاص اشاره شده است؟ اگر مسئله کاملاً مشخص و کاربردی است امتیاز ۳، اگر کلی است ۱ و در غیر این صورت ۰ بدهید.
        4.  **قابلیت تجاری‌سازی (امتیاز ۰ تا ۳):** آیا پایان‌نامه به نتایج ملموسی که قابل توسعه به محصول، نرم‌افزار، یا دستگاه باشد، اشاره می‌کند؟ اگر پتانسیل مستقیم دارد امتیاز ۳، پتانسیل غیرمستقیم ۱ و در غیر این صورت ۰ بدهید.
        5.  **همکاری با صنعت/نهاد غیردانشگاهی (امتیاز ۰ یا ۱):** آیا چکیده نشان می‌دهد با یک نهاد صنعتی یا سازمانی همکاری شده است؟ اگر بله ۱، اگر نه ۰.

        **تحلیل و خروجی:**
        پس از امتیازدهی به هر شاخص، نمره نهایی را از جمع امتیازات محاسبه کنید.
        سپس بر اساس نمره نهایی، "پتانسیل نوآوری" را طبقه‌بندی کنید:
        - **پتانسیل بالا:** نمره ۸ تا ۱۰ (و بالاتر)
        - **پتانسیل متوسط:** نمره ۵ تا ۷
        - **پتانسیل ضعیف:** نمره کمتر از ۵

        در انتها یک تحلیل کلی مختصر (حداکثر ۲ جمله) برای توجیه امتیازات ارائه دهید.

        خروجی را **دقیقا** با فرمت زیر و فقط به زبان فارسی ارائه دهید:

        حوزه علمی: [امتیاز]/3
        فناوری خاص: [امتیاز]/3
        حل مسئله: [امتیاز]/3
        تجاری‌سازی: [امتیاز]/3
        همکاری: [امتیاز]/1
        نمره نهایی: [جمع امتیازات]
        پتانسیل نوآوری: [ضعیف/متوسط/بالا]
        تحلیل کلی: [خلاصه تحلیل شما در اینجا]

        ---
        **عنوان پایان‌نامه:** {title}

        **چکیده پایان‌نامه:** {abstract}
        ---
    """

def parse_response(text):
    """
    این تابع پاسخ ساختاریافته مدل هوش مصنوعی را بر اساس معیارهای جدید تجزیه می‌کند.
    """
    data = {
        "حوزه علمی": "N/A",
        "فناوری خاص": "N/A",
        "حل مسئله": "N/A",
        "تجاری‌سازی": "N/A",
        "همکاری": "N/A",
        "نمره نهایی": "N/A",
        "پتانسیل نوآوری": "N/A",
        "تحلیل کلی": "خطا در پردازش پاسخ مدل."
    }
    try:
        lines = text.strip().split('\n')
        for line in lines:
            if "حوزه علمی:" in line:
                data["حوزه علمی"] = line.split(':')[1].strip().split('/')[0]
            elif "فناوری خاص:" in line:
                data["فناوری خاص"] = line.split(':')[1].strip().split('/')[0]
            elif "حل مسئله:" in line:
                data["حل مسئله"] = line.split(':')[1].strip().split('/')[0]
            elif "تجاری‌سازی:" in line:
                data["تجاری‌سازی"] = line.split(':')[1].strip().split('/')[0]
            elif "همکاری:" in line:
                data["همکاری"] = line.split(':')[1].strip().split('/')[0]
            elif "نمره نهایی:" in line:
                data["نمره نهایی"] = line.split(':')[1].strip()
            elif "پتانسیل نوآوری:" in line:
                data["پتانسیل نوآوری"] = line.split(':')[1].strip()
            elif "تحلیل کلی:" in line:
                data["تحلیل کلی"] = line.split(':', 1)[1].strip()
    except Exception:
        pass
    return data

def to_excel(df):
    """
    یک DataFrame را به فایل اکسل در حافظه (in-memory) تبدیل می‌کند.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='تحلیل_نوآوری')
        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(column)) + 2
            col_idx = df.columns.get_loc(column)
            writer.sheets['تحلیل_نوآوری'].set_column(col_idx, col_idx, column_length)
    processed_data = output.getvalue()
    return processed_data


# --- Streamlit App UI ---

st.title("💡 تحلیلگر هوشمند پتانسیل نوآوری پایان‌نامه‌ها")
st.markdown("این ابزار با استفاده از هوش مصنوعی Gemini و بر اساس **مدل رتبه‌بندی نوآوری**، پتانسیل پایان‌نامه‌ها را تحلیل می‌کند.")

st.sidebar.header("تنظیمات")
api_key = st.sidebar.text_input("🔑 کلید API گوگل Gemini خود را وارد کنید:", type="password", help="کلید API شما محرمانه باقی می‌ماند و فقط برای این جلسه استفاده می‌شود.")

if not api_key:
    st.warning("لطفاً برای شروع تحلیل، کلید API گوگل Gemini خود را در نوار کناری وارد کنید.")
    st.stop()

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error(f"❌ خطا در تنظیم کلید API: لطفاً از معتبر بودن کلید خود اطمینان حاصل کنید.")
    st.stop()

uploaded_file = st.file_uploader("📂 فایل اکسل حاوی عناوین و چکیده‌ها را بارگذاری کنید", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ فایل با موفقیت بارگذاری شد. لطفا ستون‌ها را مشخص کنید.")
        st.dataframe(df.head())

        st.sidebar.header("انتخاب ستون‌ها")
        columns = df.columns.tolist()
        title_col = st.sidebar.selectbox("ستون حاوی **عنوان** را انتخاب کنید:", columns, index=0)
        abstract_col = st.sidebar.selectbox("ستون حاوی **چکیده** را انتخاب کنید:", columns, index=1 if len(columns) > 1 else 0)

        if st.button("🚀 شروع تحلیل", type="primary"):
            if title_col == abstract_col:
                st.error("ستون عنوان و چکیده نمی‌توانند یکسان باشند.")
            else:
                with st.spinner("در حال تحلیل... این فرآیند ممکن است بسته به تعداد ردیف‌ها زمان‌بر باشد."):
                    progress_bar = st.progress(0, text="شروع فرآیند تحلیل...")
                    total_rows = len(df)
                    results = []

                    for i, row in df.iterrows():
                        title = str(row.get(title_col, ''))
                        abstract = str(row.get(abstract_col, ''))

                        if not title or not abstract:
                            results.append({
                                "حوزه علمی": "N/A", "فناوری خاص": "N/A", "حل مسئله": "N/A",
                                "تجاری‌سازی": "N/A", "همکاری": "N/A", "نمره نهایی": "N/A",
                                "پتانسیل نوآوری": "N/A", "تحلیل کلی": "عنوان یا چکیده موجود نیست."
                            })
                        else:
                            prompt = create_prompt(title, abstract)
                            # --- شروع بلوک تلاش مجدد ---
                            max_retries = 5
                            retry_delay = 2  # ثانیه
                            for attempt in range(max_retries):
                                try:
                                    response = model.generate_content(prompt)
                                    parsed_data = parse_response(response.text)
                                    results.append(parsed_data)
                                    break  # در صورت موفقیت، از حلقه تلاش مجدد خارج شو
                                
                                except google.api_core.exceptions.ResourceExhausted as e:
                                    if attempt < max_retries - 1:
                                        st.warning(f"محدودیت API در ردیف {i+1}. تلاش مجدد تا {retry_delay} ثانیه دیگر...")
                                        sleep(retry_delay)
                                        retry_delay *= 2  # افزایش زمان انتظار برای تلاش بعدی
                                    else:
                                        st.error(f"خطا در ردیف {i+1} پس از {max_retries} تلاش: محدودیت API ادامه دارد.")
                                        results.append({"تحلیل کلی": "خطا: محدودیت API"})
                                        break # اگر بعد از همه تلاش‌ها باز هم خطا داد، خارج شو
                                except Exception as e:
                                    st.error(f"خطا در ردیف {i+1}: {e}")
                                    results.append({"تحلیل کلی": f"خطا: {e}"})
                                    break # در صورت بروز خطای دیگر، از حلقه خارج شو
                            # --- پایان بلوک تلاش مجدد ---
                        
                        # تأخیر ثابت بین هر درخواست موفق برای جلوگیری از فشار روی API
                        sleep(1) 
                        progress_bar.progress((i + 1) / total_rows, text=f"در حال پردازش ردیف {i+1} از {total_rows}")
                    
                st.success("🎉 تحلیل با موفقیت انجام شد!")

                results_df = pd.DataFrame(results)
                results_df.rename(columns={
                    "حوزه علمی": "امتیاز حوزه علمی", "فناوری خاص": "امتیاز فناوری خاص",
                    "حل مسئله": "امتیاز حل مسئله", "تجاری‌سازی": "امتیاز تجاری‌سازی",
                    "همکاری": "امتیاز همکاری",
                }, inplace=True)
                
                final_df = pd.concat([df, results_df], axis=1)
                st.dataframe(final_df)

                excel_data = to_excel(final_df)
                st.download_button(
                    label="📥 دانلود فایل اکسل نتایج",
                    data=excel_data,
                    file_name="تحلیل_نوآوری_پایان‌نامه‌ها.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    except Exception as e:
        st.error(f"خطا در خواندن فایل اکسل: {e}")
