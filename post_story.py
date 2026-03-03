import os
import requests
import re
import time
import random
from datetime import date
from groq import Groq
from urllib.parse import quote

# ==============================================
# CONFIG & SECRETS
# ==============================================
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
page_id = os.environ.get("FB_PAGE_ID")
access_token = os.environ.get("FB_ACCESS_TOKEN")

print("DEBUG: Script started")
print(f"DEBUG: Setting Page ID: {page_id}")
print(f"DEBUG: FB_ACCESS_TOKEN length: {len(access_token) if access_token else 0}")

# ==============================================
# FACEBOOK TOKEN DIAGNOSTIC (AUTO-SWITCH ID)
# ==============================================
if access_token:
    print("--- Facebook Diagnostic Start ---")
    try:
        me_url = f"https://graph.facebook.com/v20.0/me?fields=id,name,category&access_token={access_token}"
        me_resp = requests.get(me_url)
        if me_resp.status_code == 200:
            me_data = me_resp.json()
            print(f"✅ Token represents: {me_data.get('name')} (ID: {me_data.get('id')})")
            if 'category' in me_data:
                print(f"🔄 Auto-switching Page ID to {me_data.get('id')}")
                page_id = me_data.get('id')
        else:
            print(f"❌ Token Check Failed: {me_resp.text}")
    except Exception as e:
        print(f"⚠️ Diagnostic exception: {str(e)}")
    print("--- Facebook Diagnostic End ---\n")

# ==============================================
# FACEBOOK HELPER WITH RETRIES
# ==============================================
def fb_call(url, data, file_path=None, max_retries=3):
    # Ensure current global page_id is used if URL placeholder exists
    for i in range(max_retries):
        try:
            print(f"DEBUG: FB Call Attempt {i+1}...")
            if file_path:
                with open(file_path, 'rb') as f:
                    files = {'source': ('image.jpg', f, 'image/jpeg')}
                    r = requests.post(url, data=data, files=files, timeout=90)
            else:
                r = requests.post(url, data=data, timeout=90)
            
            print(f"DEBUG: FB Status: {r.status_code}")
            if r.status_code in [200, 201]:
                return r
            
            try:
                err = r.json().get("error", {})
                if err.get("is_transient") or err.get("code") in [1, 2, 10]:
                    print(f"⚠️ FB Transient Busy (Attempt {i+1}): {err.get('message')}. Retrying in 40s...")
                    time.sleep(40)
                    continue
                else:
                    print(f"❌ FB API Error: {r.status_code} - {r.text}") # Improved error reporting
            except Exception as json_e: # Catch JSON parsing error specifically
                print(f"❌ FB Raw Error (Status: {r.status_code}): {r.text} (JSON parse error: {json_e})") # Improved error reporting
            
            return r
        except Exception as e:
            print(f"⚠️ Request exception: {str(e)}")
            time.sleep(20)
    return None

# ==============================================
# PROMPT
# ==============================================
user_prompt = """आप एक अत्यंत विद्वान, शास्त्र-निष्ठ और प्रमाणिक हिंदू धर्म कथावाचक हैं।
मुझे हर बार रैंडम रूप से चुनी गई, प्रमाणिक और अत्यंत विस्तारपूर्वक हिंदू धर्म कथा सुनाइए।

⚠️ अनिवार्य नियम:
1. कथा कम से कम 8-10 लंबे अनुच्छेदों (Paragraphs) में होनी चाहिए। (Target: 800 words)
2. हर संवाद, दृश्य और भावना का गहरा वर्णन करें। 
3. "Image Generation Prompts - ENGLISH ONLY" सेक्शन में 5-7 विस्तृत AI prompts ENGLISH में दें।
"""

full_prompt = user_prompt + """
Output exactly in this format:

[Title in Hindi]

[Story - 8+ Paragraphs - 800 words - Elaborate deeply]

— यह कथा किस ग्रंथ से ली गई है और कौन-सा प्रसंग है: [source]

Image Generation Prompts - ENGLISH ONLY
1. [Prompt 1]
2. [Prompt 2]
...
"""

# ==============================================
# CALL GROQ
# ==============================================
print("Calling Groq for story...")
full_output = "कथा उत्पन्न नहीं हो सकी।"
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.7,
        max_tokens=3500
    )
    full_output = response.choices[0].message.content.strip()
    print("Groq success. Output len:", len(full_output))
except Exception as e: print("Groq error:", str(e))

# ==============================================
# PARSING
# ==============================================
print("Parsing output...")
story_parts = full_output.split("Image Generation Prompts")
story_main = story_parts[0].strip()
lines = [l.strip() for l in story_main.splitlines() if l.strip()]
title = lines[0] if lines else "प्रमाणिक हिंदू कथा"

# Improved word count & source extraction
word_count = len(story_main.split())
print(f"DEBUG: Story word count: ~{word_count} words")

source_match = re.search(r'— यह कथा किस ग्रंथ से ली गई है और कौन-सा प्रसंग है: (.+)', full_output, re.IGNORECASE)
if not source_match:
    source_match = re.search(r'— (.+)', lines[-1])
source = source_match.group(1).strip() if source_match else "प्राचीन शास्त्र"

img_prompts = re.findall(r'\d+\.\s*(.+)', story_parts[-1] if len(story_parts)>1 else "")
print(f"Found {len(img_prompts)} prompts.")

# ==============================================
# IMAGES (STABLE WATERFALL & LOCAL CAPTURE)
# ==============================================
print("Generating images...")
main_image_path = os.path.join(os.getcwd(), "story_image.jpg")
image_urls_log = []

for i, base_p in enumerate(img_prompts[:7]):
    try:
        sd = random.randint(1, 999999)
        p_enc = quote(base_p[:200] + ", vibrant, spiritual, highly detailed, 4k")
        image_urls_log.append(f"https://image.pollinations.ai/prompt/{p_enc}?width=1024&height=1024&seed={sd}")
        
        if i == 0:
            success = False
            provs = [
                {"n": "Hercai", "u": f"https://hercai.onrender.com/v3/text2image?prompt={p_enc}"},
                {"n": "Unsplash", "type": "search"},
                {"n": "Pollinations-Turbo", "u": f"https://image.pollinations.ai/prompt/{p_enc}?width=1024&height=1024&model=turbo&nologo=true&seed={sd}"}
            ]
            
            for p in provs:
                print(f"DEBUG: Trying {p['n']}...")
                try:
                    d = None
                    if p.get("type") == "search":
                        sub_kws = ["krishna", "shiva", "rama", "hanuman", "ganesha", "durga", "vishnu", "hindu", "temple", "spiritual"]
                        story_low = story_main.lower()
                        kw = "hindu deity"
                        for k in sub_kws:
                            if k in story_low: kw = k; break
                        
                        fallback_ids = {
                            "krishna": "1627844718626-4c6b96366607",
                            "shiva": "1641320349487-ce111bd290f6",
                            "temple": "1590766940554-634a7ed41450"
                        }
                        fid = fallback_ids.get(kw, fallback_ids["temple"])
                        r = requests.get(f"https://images.unsplash.com/photo-{fid}?q=80&w=1024", timeout=30)
                        if r.status_code == 200: d = r.content
                    else:
                        r = requests.get(p['u'], timeout=45)
                        if r.status_code == 200:
                            if p['n'] == "Hercai":
                                u = r.json().get("url")
                                if u: d = requests.get(u, timeout=30).content
                            else: d = r.content
                    
                    if d and d.startswith(b'\xff\xd8'):
                        with open(main_image_path, "wb") as f: f.write(d)
                        print(f"✅ Image Success! ({p['n']})")
                        success = True
                        break
                except: pass
            
            if not success:
                print("❌ waterfall failed. Using Krishna fallback.")
                r = requests.get("https://images.unsplash.com/photo-1627844718626-4c6b96366607?q=80&w=1024", timeout=20)
                with open(main_image_path, "wb") as f: f.write(r.content)
        time.sleep(1)
    except: pass

# ==============================================
# FACEBOOK POST
# ==============================================
if os.path.exists(main_image_path) and access_token:
    print(f"Posting to Facebook (Page ID: {page_id})...")
    caption = f"{title}\n\n{story_main[:5000]}\n\n🙏 #SanatanDharma #HinduKatha #Bhakti"

    # 1. Post to Feed directly
    print("Action: Creating Feed Post...")
    try:
        up_url = f"https://graph.facebook.com/v20.0/{page_id}/photos"
        payload_feed = {
            'message': caption,
            'published': 'true',
            'access_token': access_token
        }
        feed_r = fb_call(up_url, payload_feed, file_path=main_image_path, max_retries=3)
        
        if feed_r and feed_r.status_code in [200, 201]:
            print(f"✅ SUCCESS! Feed Post ID: {feed_r.json().get('post_id', feed_r.json().get('id'))}")
        else:
            print(f"❌ Feed Post failed.")
    except Exception as e:
        print(f"❌ FB Feed error: {str(e)}")

    # 2. Post to Story
    print("Action: Creating Story Post...")
    try:
        up_url = f"https://graph.facebook.com/v20.0/{page_id}/photos"
        payload_story = {
            'published': 'false', 
            'access_token': access_token
        }
        upload_r = fb_call(up_url, payload_story, file_path=main_image_path, max_retries=3)
        
        if upload_r and upload_r.status_code in [200, 201]:
            pid = upload_r.json().get('id')
            print(f"✅ Photo Uploaded for Story (ID: {pid})")
            
            story_r = requests.post(f"https://graph.facebook.com/v20.0/{page_id}/photo_stories", 
                          data={'photo_id': pid, 'access_token': access_token}, timeout=40)
            if story_r.status_code in [200, 201]:
                print("✅ Story posted!")
            else:
                print(f"❌ Story failed: {story_r.text}")
        else:
            print("❌ Photo upload for story failed.")
    except Exception as e:
        print(f"❌ FB Story error: {str(e)}")

else: print("Skipping post (Missing image or token)")

print("\nREELS IMAGES:")
for i, url in enumerate(image_urls_log[1:], 2): print(f"Image {i}: {url}")
