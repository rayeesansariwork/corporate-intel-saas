import re
import logging

logger = logging.getLogger("Tech_Hunter")

class TechHunter:
    def __init__(self):
        # Fingerprints for expensive B2B software
        self.signatures = {
            # --- ADVERTISING (High Intent) ---
            "Facebook Ads (Pixel)": [r"connect\.facebook\.net/en_US/fbevents\.js", r"fbq\('init'"],
            "LinkedIn Insights": [r"snap\.licdn\.com/li\.lms-analytics", r"linkedin_data_partner_id"],
            "Google Ads (Gtag)": [r"googletagmanager\.com/gtag/js", r"google_conversion_id"],
            "Twitter Ads": [r"static\.ads-twitter\.com/uwt\.js"],

            # --- ANALYTICS & UX ---
            "Google Analytics 4": [r"G-[A-Z0-9]{10}", r"googletagmanager\.com/gtag/js"],
            "Hotjar (Heatmaps)": [r"static\.hotjar\.com", r"hj\('trigger'"],
            "CrazyEgg": [r"script\.crazyegg\.com/pages/scripts"],
            "Mixpanel": [r"cdn\.mxpnl\.com/libs/mixpanel"],

            # --- CRM & SALES (Big Budgets) ---
            "HubSpot": [r"js\.hs-scripts\.com", r"hs-script-loader"],
            "Salesforce": [r"salesforce\.com", r"force\.com", r"pardot"],
            "Intercom": [r"widget\.intercom\.io"],
            "Drift": [r"js\.drift\.com"],
            "Zendesk": [r"static\.zdassets\.com"],

            # --- E-COMMERCE ---
            "Shopify": [r"cdn\.shopify\.com", r"Shopify\.theme"],
            "WooCommerce": [r"wp-content/plugins/woocommerce"],
            "Magento": [r"static/version", r"mage/cookies"],

            # --- INFRASTRUCTURE ---
            "Vercel": [r"_next/static"],
            "Stripe": [r"js\.stripe\.com"],
            "Cloudflare": [r"cdnjs\.cloudflare\.com"]
        }

    def scan(self, html_content: str):
        """
        Scans raw HTML for specific JavaScript signatures.
        """
        detected = []
        if not html_content:
            return detected

        for tech_name, patterns in self.signatures.items():
            for pattern in patterns:
                # We use IGNORECASE to catch variations
                if re.search(pattern, html_content, re.IGNORECASE):
                    detected.append(tech_name)
                    break # Found it, stop checking other patterns for this specific tech
        
        if detected:
            logger.info(f"🕵️ Detected Tech: {', '.join(detected)}")
            
        return detected