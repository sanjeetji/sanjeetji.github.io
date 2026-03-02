import os
import requests
import re
from datetime import date
from groq import Groq
from urllib.parse import quote

# ==============================================
# CONFIG & DEBUG SECRETS
# ==============================================
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
page_id = os.environ.get("FB_PAGE_ID")
access_token = os.environ.get("FB_ACCESS_TOKEN")

print("DEBUG: Script started")
print(f"DEBUG: GROQ_API_KEY present: {'YES' if os.environ.get('GROQ_API_KEY') else 'NO'}")
print(f"DEBUG: FB_PAGE_ID: {page_id}")
print(f"DEBUG: FB_ACCESS_TOKEN length: {len(access_token) if access_token else 0}")

today = date.today().strftime("%d %B %Y")

# ==============================================
# PROMPT
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
# CALL GROQ
# ==============================================
print("Calling Groq for story...")
full_output = ""
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.65,
        max_tokens=1800
    )
    full_output = response.choices[0].message.content.strip()
    print("Groq success. Output length:", len(full_output))
except Exception as e:
    print("Groq error:", str(e))
    full_output = "कथा उत्पन्न नहीं हो सकी।"

# ==============================================
# SAFE PARSING
# ==============================================
print("Parsing output...")

# Title - first line
title = "प्रमाणिक हिंदू कथा"
if full_output:
    lines = [line.strip() for line in full_output.splitlines() if line.strip()]
    if lines:
        title = lines[0]

# Story text
story_end = len(full_output)
for kw in ["— यह कथा किस ग्रंथ", "Image Generation Prompts", "Image prompts"]:
    pos = full_output.lower().find(kw.lower())
    if pos != -1 and pos < story_end:
        story_end = pos
story_text = full_output[:story_end].strip()

# Source
source = "प्रमाणिक हिंदू ग्रंथ (स्रोत स्पष्ट नहीं)"
source_match = re.search(r'—\s*यह\s*कथा\s*किस\s*ग्रंथ\s*से\s*ली\s*गई\s*है\s*और\s*कौन-सा\s*प्रसंग\s*है\s*:\s*(.+?)(?=\s*Image|\Z)', full_output, re.IGNORECASE | re.DOTALL)
if source_match:
    source = source_match.group(1).strip()
print("Parsed source:", source)

# Image prompts
img_prompts = re.findall(r'\d+\.\s*(.+?)(?=\n\d+\.|\Z)', full_output, re.DOTALL)
print("Image prompts found:", len(img_prompts))

# ==============================================
# IMAGES
# ==============================================
print("Generating images...")
image_urls = []
main_image_path = "/tmp/story_main.jpg"

fallback_prompt = "Beautiful traditional Hindu devotional scene of Lord Shiva on Kailash, serene, vibrant colors, no text"

for i, base_prompt in enumerate(img_prompts[:7] or [fallback_prompt]):
    try:
        full_prompt = base_prompt.strip() + ", traditional Hindu devotional art style, vibrant colors, highly detailed, cinematic lighting, serene atmosphere, no text, no watermark, 4k"
        encoded = quote(full_prompt)
        img_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=576&model=flux&nologo=true&safe=true"
        
        if i == 0:
            resp = requests.get(img_url, timeout=25)
            if resp.status_code == 200:
                with open(main_image_path, "wb") as f:
                    f.write(resp.content)
                print("Main image OK")
            else:
                print("Image download failed:", resp.status_code)
        
        image_urls.append(img_url)
        print(f"Image {i+1}: {img_url}")
    except Exception as e:
        print(f"Image {i+1} error:", str(e))

# ==============================================
# FACEBOOK POST
# ==============================================
print("Posting to Facebook...")
if os.path.exists(main_image_path):
    try:
        caption = f"""{title}

{story_text}

— यह कथा किस ग्रंथ से ली गई है और कौन-सा प्रसंग है: {source}

🙏 जय श्री राम | हर हर महादेव
#SanatanDharma #HarHarMahadev #HinduKatha #DailyKatha #Bhakti

🔥 Poori story Reel mein dekhne ke liye comment "REEL" likho"""

        url = f"https://graph.facebook.com/v20.0/{page_id}/photos"
        payload = {'message': caption, 'access_token': access_token}
        files = {'source': open(main_image_path, 'rb')}

        resp = requests.post(url, data=payload, files=files, timeout=40)
        if resp.status_code in [200, 201]:
            print("✅ Post successful!")
            print("FB Response:", resp.json())
        else:
            print("FB Error:", resp.status_code, resp.text)
    except Exception as e:
        print("FB Post exception:", str(e))
else:
    print("No main image - skipping post")

# ==============================================
# REELS LINKS
# ==============================================
print("\nREELS IMAGES:")
for i, url in enumerate(image_urls[1:], 2):
    print(f"Image {i}: {url}")
print("\nLinks save kar lo for CapCut")
