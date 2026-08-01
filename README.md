# Recruitment Project

A Django-based recruitment application for applicant registration, HR job postings, application tracking, and interview scheduling.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Apply migrations:
   ```bash
   python manage.py migrate
   ```
4. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Notes

- The HR registration invite code is currently set in `recruitment/forms.py`.
- Uploaded resumes are stored under `media/application_resumes/`.
- Update `config/settings.py` for production configuration.
