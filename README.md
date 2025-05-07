## YouTube Tutorial

For a walkthrough on how to use and modify this bot, check out the tutorial video:  
**https://youtu.be/rffINf2G2TA**

The video covers how to:
1. Edit a question on the form
2. Add a PDF SOP to the training data
3. Assign a person as a **farmer/operator**
4. Assign a person as a **technician**

---

## Edit the Files in `forms/`

- `daily_form.py`
- `weekly_form.py`

Each form field follows this structure:

```python
{
  "key": "do",
  "name": "DO (mg/L)",
  "prompt": "Berapa nilai DO hari ini?",
  "require_photo": True
}
Adjust Alert Thresholds

Edit ai_helper.py:

ALERT_THRESHOLDS = {
  "do": {"min": 4.0, "max": 7.5},
  "ph": {"min": 6.5, "max": 8.5},
  ...
}
Update Reminder Schedule

Edit scheduler.py → schedule_jobs():

scheduler.add_job(send_daily_reminder, 'cron', hour=7, minute=30)
scheduler.add_job(send_weekly_reminder, 'cron', day_of_week='sun', hour=5, minute=0)
All times are in UTC.

Change Sandbox Timeout Behavior

In scheduler.py → update_last_reactivation():

run_time = datetime.utcnow() + timedelta(hours=1)
This schedules a reminder 1 hour before sandbox expiration. You can adjust this to any time before the 72-hour limit.

Test Commands

Command	Behavior
test	Manually start the form
test troubleshoot	Sends fake out-of-range data to experts
test health status	Sends a full test report with video
join sense-believed	Updates sandbox reactivation tracking
Deployment Instructions

One-Time Heroku Setup
heroku create
heroku buildpacks:set heroku/python
heroku config:set $(cat .env | xargs)
git push heroku main
Redeploy After Changes
git add .
git commit -m "Your message"
git push heroku main

You can copy and paste this directly into your `README.md` file on GitHub. Want a downloadable version too?
