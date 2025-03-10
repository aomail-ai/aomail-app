export BACKEND_PORT=8010
export FRONTEND_PORT=8090
export SERVER_FRONTEND_PORT=8080 # 8080 for dev, 80 for prod
export DB_PORT=5490
export ENV="aomail"
export NODE_ENV="development" # "development" or "production"
export POSTGRES_USER="test"
export POSTGRES_PASSWORD="test"
export POSTGRES_DB="aomaildb"
export ALLOWED_HOSTS="localhost:8010"
export BASE_URL="http://localhost:8090/";
export API_BASE_URL="http://localhost:8010/aomail/";

if [ $NODE_ENV = "development" ]; then
    echo "Starting in development mode"
    docker compose -p ${ENV}_project up --build -d frontend_dev backend_dev
    container_name="${ENV}_project-backend_dev-1"
elif [ $NODE_ENV = "production" ]; then
    echo "Starting in production mode"
    docker compose -p ${ENV}_prod up --build -d frontend_prod backend_prod
    container_name="${ENV}_prod-backend_prod-1"
fi

# Extract the ID of the Google renew subscription
ID=""
while [ -z "$ID" ]; do
  ID=$(docker exec -i $container_name crontab -l 2>/dev/null | grep 'crontab run' | awk -F 'run ' '{print $2}' | awk '{print $1}' | head -n 1)
  if [ -z "$ID" ]; then
    echo "No ID found. Retrying in 5 seconds..."
    sleep 5
  fi
done
echo "ID found: $ID"

# Get the absolute path of the script's directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Define the cron job with the log file located in the same directory as the script
CRON_JOB="0 3 * * * docker exec -i ${container_name} /usr/local/bin/python /app/manage.py crontab run $ID >> $SCRIPT_DIR/aomail-cron.log 2>&1"

# Add cron job if it doesn’t already exist
(crontab -l | grep -F "$CRON_JOB") && echo "Cron job already exists" || (crontab -l; echo "$CRON_JOB") | crontab -
