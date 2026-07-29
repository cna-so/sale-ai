IMAGE_PROMPT_FA = """\
تصویر محصول را تحلیل کن و فقط JSON معتبر برگردان با این فیلدها:
- product_category
- concise_description
- visual_attributes (array of strings)
- suggested_search_query
- confidence

قوانین:
- suggested_search_query باید کوتاه و مناسب جستجوی محصول باشد
- اگر locale فارسی است، suggested_search_query را فارسی تولید کن
- confidence عددی بین 0 و 1 باشد
- متن اضافه خارج از JSON ممنوع است
"""

IMAGE_PROMPT_EN = """\
Analyze the product image and return only valid JSON with:
- product_category
- concise_description
- visual_attributes (array of strings)
- suggested_search_query
- confidence

Rules:
- suggested_search_query should be concise and suitable for product search
- If locale is Persian, suggested_search_query should be in Persian; otherwise English
- confidence must be a number between 0 and 1
- No extra text outside JSON
"""

IMAGE_DESC_PROMPT_FA = """\
این تصویر یک محصول فروشگاهی است.
در حداکثر دو جمله کوتاه فارسی بگو این محصول چیست و چه ویژگی‌های دیداری مهمی دارد.
اگر ممکن است یک عبارت کوتاه مناسب جستجو در دیجی‌کالا هم پیشنهاد بده.
JSON ننویس.
"""

IMAGE_DESC_PROMPT_EN = """\
This image shows a retail product.
In at most two short sentences, describe what the product is and its key visual attributes.
Also suggest a short shopping search phrase if possible.
Do not write JSON.
"""
