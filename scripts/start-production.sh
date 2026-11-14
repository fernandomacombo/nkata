#!/bin/sh
set -eu

if [ "${NKATA_PROCESS_TYPE:-web}" = "worker" ] || [ "${NKATA_PROCESS_TYPE:-web}" = "payments" ]; then
  attempts=0
  until python manage.py migrate --check >/dev/null 2>&1 && python manage.py check_nkata_runtime >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [ "$attempts" -ge 30 ]; then
      echo "As migrações não ficaram prontas dentro de 60 segundos." >&2
      exit 1
    fi
    sleep 2
  done
  if [ "${NKATA_PROCESS_TYPE:-web}" = "payments" ]; then
    exec python manage.py reconcile_nkata_payments --watch --interval 60
  fi
  exec python manage.py run_nkata_media_moderation_worker --watch
fi

python manage.py migrate --noinput
python manage.py check_nkata_runtime
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
