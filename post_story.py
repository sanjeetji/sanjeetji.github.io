import os
import requests
import re
from datetime import date
from groq import Groq
from urllib.parse import quote

# ==============================================
# CONFIG & SECRETS
# ==============================================
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
page_id = os.environ.get("FB_PAGE_ID")
access_token = os.environ.get("FB_ACCESS_TOKEN")

today = date.today().strftime("%d %B %Y")

print("DEBUG: Starting script...")
print(f"DEBUG: GROQ_API_KEY present: {'yes' if os.environ.get('GROQ_API_KEY') else 'NO'}")
print(f"DEBUG: FB_PAGE_ID: {page_id}")
print(f"DEBUG: FB_ACCESS_TOKEN length: {len(access_token) if access_token else 0}")

# ==============================================
# TUMHARA EXACT PROMPT
# ==============================================
user_prompt = """आप एक अत्यंत विद्वान, शास्त्र-निष्ठ और प्रमाणिक हिंदू धर्म कथावाचक हैं।
मुझे हर बार रैंडम रूप से चुनी गई, लेकिन पूरी तरह सत्य और ग्रंथों पर आधारित एक हिंदू धर्म कथा सुनाइए।
कथा केवल और केवल निम्न प्रमाणिक स्रोतों से ली जाए:
उपनिषद,
चारों वेदों से जुड़े आख्यान,
18 महापुराण एवं उपपुराण,
श्रीमद्भागवत पुराण,
शिव पुराण,
महाभारत,
रामायण,
भगवद्गीता,
और अन्य मान्य व प्रमाणिक हिंदू धर्मग्रंथ।
⚠️ बहुत महत्वपूर्ण नियम:
कहानी पूरी तरह मूल शास्त्रों पर आधारित हो —
कोई कल्पना, आधुनिक बदलाव, फिक्शनल दृश्य या मनगढ़ंत पात्र न जोड़े जाएँ।
हर बार किसी एक वास्तविक प्रसंग, घटना या संवाद को रैंडम रूप से चुनिए।
भाषा केवल सरल, शुद्ध और भावपूर्ण हिंदी में हो।
📖 Story ka title in hindi sabse upar
कहानी कम से कम 260 शब्दों की हो और 1–2 मिनट में सुनाई जा सके।
कहानी में पात्रों के संवाद, वातावरण और भावनाएँ हों —
लेकिन किसी भी तथ्य या क्रम में परिवर्तन न किया जाए।
किसी भी प्रकार का आधुनिक उदाहरण, तुलना, मोटिवेशनल भाषण या निजी राय शामिल न हो।
कहानी समाप्त होने के बाद स्पष्ट रूप से यह लिखें:
— यह कथा किस ग्रंथ से ली गई है और कौन-सा प्रसंग है।
इसके बाद एक अलग सेक्शन में यह भी दें:
“Image Generation Prompts (Story based)”
जहाँ उसी कहानी के आधार पर
कम से कम 5 से 7 अलग-अलग दृश्यों के लिए
AI image बनाने योग्य, स्पष्ट और दृश्य-प्रधान prompts दिए जाएँ।
हर image prompt में यह स्पष्ट हो:
कौन-सा पात्र है
स्थान (वन, आश्रम, युद्धभूमि, कैलाश, अयोध्या, द्वारका आदि)
समय या भाव (शांति, युद्ध, करुणा, भक्ति, संकट, विजय आदि)
दृश्य का मुख्य केंद्र क्या है
Image prompts केवल दृश्य वर्णन के लिए हों —
उनमें कहानी दोबारा न लिखी जाए।
अब उपरोक्त सभी नियमों का पालन करते हुए
एक प्रमाणिक हिंदू धर्म कथा प्रारंभ करें।"""

full_prompt = user_prompt + """
Output exactly is format mein (kuch extra mat add karna):

[Title in Hindi]

[poori kahani 260+ words]

— यह कथा किस ग्रंथ से ली गई है और कौन-सा प्रसंग है: [source]

Image Generation Prompts (Story based)
1. [prompt 1]
2. [prompt 2]
3. [prompt 3]
4. [prompt 4]
5. [prompt 5]
6. [prompt 6]
7. [prompt 7]"""

# ==============================================
# GENERATE STORY FROM GROQ
# ==============================================
print("Generating story from Groq...")
full_output = ""
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.65,
        max_tokens=1800
    )
    full_output = response.choices[0].message.content.strip()
    print("DEBUG: Groq response received. Length:", len(full_output))
    # Optional: print first 500 chars for debug (comment out later)
    # print("DEBUG: First 500 chars:", full_output[:500])
except Exception as e:
    print("ERROR: Groq API call failed:", str(e))
    full_output = ""

# ==============================================
# SAFE PARSING WITH FALLBACKS
# ==============================================
print("Parsing LLM output...")

# Title (first non-empty line)
title = "प्रमाणिक हिंदू कथा"
if full_output:
    lines = [line.strip() for line in full_output.splitlines() if line.strip()]
    if lines:
        title = lines[0]

# Story text (until source line)
story_end_keywords = [
    "— यह कथा किस ग्रंथ",
    "यह कथा किस ग्रंथ",
    "Image Generation Prompts",
    "Image prompts"
]
story_end = len(full_output)
for kw in story_end_keywords:
    pos = full_output.find(kw)
    if pos != -1 and pos < story_end:
        story_end = pos
story_text = full_output[:story_end].strip()

# Source (very flexible regex)
source = "प्रमाणिक हिंदू ग्रंथ से लिया गया प्रसंग (स्रोत स्पष्ट नहीं मिला)"
source_patterns = [
    r'—\s*यह कथा किस ग्रंथ से ली गई है और कौन-सा प्रसंग है\s*:\s*(.+?)(?=\s*Image|\Z)',
    r'यह कथा किस ग्रंथ.*?:?\s*(.+?)(?=\s*Image|\Z)',
    r'ग्रंथ.*?:?\s*(.+?)(?=\s*Image|\Z)'
]
for pattern in source_patterns:
    match = re.search(pattern, full_output, re.IGNORECASE | re.DOTALL)
    if match:
        source = match.group(1).strip()
        break
print("DEBUG: Parsed Source:", source)

# Image prompts (fallback if none found)
img_prompts = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\Z)', full_output, re.DOTALL)
if not img_prompts:
    img_prompts = ["Beautiful traditional Hindu devotional scene of Lord Shiva meditating on Kailash"]
print("DEBUG: Found image prompts:", len(img_prompts))

# ==============================================
# GENERATE IMAGES
# ==============================================
print("🎨 Generating images...")
image_urls = []
main_image_path = "/tmp/daily_story_main.jpg"

for i, base_prompt in enumerate(img_prompts[:7]):
    try:
        full_img_prompt = base_prompt.strip() + ", traditional Hindu devotional art style, vibrant colors, highly detailed, cinematic lighting, serene atmosphere, no text, no watermark, 4k"
        encoded = quote(full_img_prompt)
        img_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&model=flux&nologo=true&safe=true"
        
        if i == 0:
            img_response = requests.get(img_url, timeout=25)
            if img_response.status_code == 200:
                with open(main_image_path, "wb") as f:
                    f.write(img_response.content)
                print("Main image downloaded successfully")
            else:
                print(f"Main image download failed (status {img_response.status_code})")
        
        image_urls.append(img_url)
        print(f"✅ Image {i+1} ready → {img_url}")
    except Exception as e:
        print(f"Image {i+1} generation error:", str(e))

# ==============================================
# FACEBOOK POST
# ==============================================
print("Attempting Facebook post...")
if os.path.exists(main_image_path):
    try:
        full_caption = f"""{title}

{story_text}

— यह कथा किस ग्रंथ से ली गई है और कौन-सा प्रसंग है: {source}

🙏 जय श्री राम | हर हर महादेव
#SanatanDharma #HarHarMahadev #HinduKatha #DailyKatha #Bhakti

🔥 Poori story Reel mein dekhne ke liye comment "REEL" likho"""

        post_url = f"https://graph.facebook.com/v20.0/{page_id}/photos"
        payload = {'message': full_caption, 'access_token': access_token}
        files = {'source': open(main_image_path, 'rb')}

        r = requests.post(post_url, data=payload, files=files, timeout=40)
        if r.status_code in (200, 201):
            print("✅ Facebook post successful!")
            print("Response:", r.json())
        else:
            print("❌ FB API error:", r.status_code, r.text)
    except Exception as e:
        print("Facebook posting exception:", str(e))
else:
    print("Main image file missing - skipping FB post")

# ==============================================
# REELS EXTRA IMAGES
# ==============================================
print("\n🎥 REELS KE LIYE EXTRA IMAGES:")
for i, url in enumerate(image_urls[1:], 2):
    print(f"Image {i}: {url}")
print("\nBas in links ko browser mein khol ke save kar lo → CapCut mein daal do!")
