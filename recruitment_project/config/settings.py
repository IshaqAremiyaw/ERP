import dj_database_url
import os

ALLOWED_HOSTS = ['Jobseeker.onrender.com', 'localhost', '127.0.0.1']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # add right after security
    # ...rest of your existing middleware stays the same
]

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('jobseeker_b27e'),
        conn_max_age=600
    )
}

DEBUG = False

CSRF_TRUSTED_ORIGINS = ['https://Jobseeker.onrender.com']