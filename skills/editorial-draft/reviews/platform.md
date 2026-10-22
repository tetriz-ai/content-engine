# Platform Reviewer — Publishing Readiness

## Activation
Run automatically as Reviewer 7 during Phase 4, or invoke with: `rerun platform`
Requires: The writer must specify the target platform during Style Setup or Interview. If unknown, ask: "Where will this be published?"

---

## Platform: LinkedIn

**Length:** Sweet spot 200-300 words (short post), 500-800 words (article). Posts over 1,300 characters truncated behind "...see more" — hook MUST land before that cutoff.

**Formatting:** One sentence per line. Short paragraphs (1-2 sentences). No markdown headers. Bold for emphasis on 1-2 key phrases only.

**Hook:** First line is EVERYTHING. Test: cover the first line — does the rest make you want to uncover it? Flag: "I'm excited to share...", "Thrilled to announce...", "5 Tips for..."

**Engagement:** End with genuine question inviting stories (not yes/no). Flag lazy CTAs: "Agree?", "Thoughts?" Flag >5 hashtags. Flag external links in body (suggest first comment).

**Tone:** Personal > corporate. "I" not "we". Flag press releases, humblebrags.

---

## Platform: Company Blog / Medium / Substack

**Length:** Blog 1,200-2,000 words. Medium optimal 1,600 words (~7 min read). Substack 800-2,500 words.

**SEO (Company Blog):** Flag if H1/title missing primary keyword. Flag no meta description in first 155 chars. Flag no internal/external links. Flag keyword stuffing (>3% density).

**Formatting:** Subheadings every 300-400 words. Short paragraphs (3-4 sentences). Table of contents for posts >1,500 words.

**Readability:** Target Grade 8-10 (Flesch-Kincaid). Flag sentences >25 words. Flag paragraphs >4 sentences. Flag >500 words without visual break.

**Metadata Checklist:**
- ☐ Title (under 60 characters for SEO)
- ☐ Subtitle / meta description (under 155 characters)
- ☐ Featured image suggestion
- ☐ Category / tags
- ☐ CTA at end

---

## Platform: Email Newsletter

**Length:** Single-topic 500-1,000 words. Multi-topic 800-1,500 words.

**Subject Line:** Under 50 characters. Flag generic: "Weekly Update", "Newsletter #47". Suggest 2-3 alternatives.

**Email-Specific:** Flag embedded videos, complex CSS, interactive elements. Flag images without alt text. Flag >3 CTAs. Primary CTA above fold.

**Tone:** More intimate than blog. "You" > "we". Flag broadcasts that should feel like letters. Flag if no personal element.

---

## Platform: Twitter/X Thread

**Length:** Individual tweet 280 chars max. Thread 5-15 tweets optimal. Flag >20 tweets.

**Hook (Tweet 1):** Must work standalone. Flag "Thread:" or "🧵" without hook first.

**Structure:** Tweet 1: Hook/bold claim → Tweets 2-3: Context → Tweets 4-N: Evidence/story → Last: Takeaway + CTA.

**Media:** Suggest where to add images/screenshots. Flag text-only threads >10 tweets.

---

## Platform: Internal (Slack / Notion / Confluence)

**Length:** Slack <500 words. TL;DR required for >300 words.

**Action Orientation:** Flag if no clear "what do you need from me?" signal. Decision docs: recommendation in first paragraph. RFCs: flag no "Alternatives Considered."

**Audience:** Flag if assumed audience unclear. Flag detail level mismatch.

---

## Output Format

```
PLATFORM: [detected or specified platform]

Platform Compliance Checklist:
✅/❌ [requirement] — [status and fix if needed]

Issues:
[CRITICAL|IMPORTANT|NICE_TO_HAVE] — "relevant text or missing element"
Problem: [what's wrong for this platform]
Fix: [specific suggestion]

Metadata Suggestions (if applicable):
- Title: [optimized version]
- Subtitle / Meta description: [suggestion]
- Subject line options: [if newsletter]
- Tags/hashtags: [suggestions]
```

End with:
- **Platform readiness:** READY / NEEDS_TWEAKS / NOT_READY
- **#1 thing to fix** before publishing on this platform
