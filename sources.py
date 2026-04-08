SOURCES = [
    {
        "name": "PBSA News",
        "domain": "pbsanews.co.uk",
        "feed_url": "https://www.pbsanews.co.uk/feed/",
    },
    # Add further sources here. Each entry needs:
    #   name      -- display name shown on cards
    #   domain    -- used for attribution label
    #   feed_url  -- RSS/Atom feed URL for the source
]

EMAIL_RECIPIENTS = [
    # Add recipient email addresses here, e.g. "colleague@thedotgroup.com"
]

EMAIL_SENDER_ADDRESS = "digest@yourdomain.com"   # must be a verified sender in Brevo
EMAIL_SENDER_NAME = "PBSA News Digest"
EMAIL_SUBJECT = "PBSA News Digest -- {date}"     # {date} replaced at send time
