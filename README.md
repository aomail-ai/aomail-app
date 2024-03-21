# Repository for MailAssistant

## Quick Setup

```bash
# Install WSL (Debian distribution)
wsl --install -d Debian

# Update system and install necessary tools
sudo apt update
sudo apt install git
sudo apt install npm
sudo apt install postgresql

# replace prodvX by the current version
git clone -b prodvX https://your_pseudo:token@github.com/Teh45/MailAssistant.git

pip install -r requirements.txt
```

## Local Development Setup
If you're developing on localhost, it's recommended to install the following browser extensions to handle CORS (Cross-Origin Resource Sharing) issues:

### Chrome Extensions:
- [CORS Unblock](https://chromewebstore.google.com/detail/cors-unblock/lfhmikememgdcahcdlaciloancbhjino)
- [Allow CORS Access-Control](https://chromewebstore.google.com/detail/allow-cors-access-control/lhobafahddgcelffkeicbaginigeejlf)

### Firefox Add-ons:
- [CORS Unblock](https://addons.mozilla.org/en-US/firefox/addon/cors-unblock/)
- [Access-Control-Allow-Origin](https://addons.mozilla.org/en-US/firefox/addon/access-control-allow-origin/)

### Microsoft Edge Extensions:
- [CORS Unblock](https://microsoftedge.microsoft.com/addons/detail/cors-unblock/hkjklmhkbkdhlgnnfbbcihcajofmjgbh?hl=es)
- [Allow CORS AccessControl](https://microsoftedge.microsoft.com/addons/detail/allow-cors-accesscontro/bhjepjpgngghppolkjdhckmnfphffdag)

# COMMON ISSUES
**M365 Licenses Error:**
If you encounter the following error while accessing data:
```json
{
  "error": {
    "code": "MailboxNotEnabledForRESTAPI",
    "message": "The mailbox is either inactive, soft-deleted, or is hosted on-premise."
  }
}
```
This error typically indicates that your account does not have the proper license to access the requested data thus you have to pay a M365 license.

# Test Reply Later
curl -X GET \
     -H "Authorization: Bearer access" \
     -H "email: test.mailassistantprod@gmail.com" \
     "https://augustin.aochange.com/MailAssistant/api/save_last_mail"

# Database Suppression

**Note:** Ensure that you have stopped the backend server before attempting to drop the database.

```sql
sudo -u postgres psql
\c postgres
DROP DATABASE mailassistantdb;
```


## Database Configuration
# Start PostgreSQL service and configure the database
```sql
sudo service postgresql start
sudo -u postgres psql
CREATE DATABASE mailassistantdb;
CREATE USER django_admin WITH PASSWORD 'admin@2';
GRANT ALL PRIVILEGES ON DATABASE mailassistantdb TO django_admin;
\c mailassistantdb
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO django_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO django_admin;
GRANT ALL ON SCHEMA public TO django_admin;
```

## Starting the Servers
# Grant execution permissions and start servers
```bash
chmod +x start_servers.sh
sudo ./start_servers.sh
```

## Gmail API Authentication & Backend Server Termination

To test Gmail API authentication, utilize the provided `curl` command. Replace `YOUR_ACCESS_TOKEN` with your actual access token.

### Testing Authentication:
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://augustin.aochange.com/MailAssistant/api/authenticate-service
```

### Stopping the Backend Server:
To stop the backend server running on port 9000, execute the following command:

```bash
sudo kill $(sudo lsof -t -i:9000)
```
