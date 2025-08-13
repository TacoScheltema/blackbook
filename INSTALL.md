# Installation and Setup Guide

This document provides instructions on how to set up and run the LDAP Address Book application on your local machine.

## 1. Prerequisites

Before you begin, ensure you have the following installed on your system:
* **Python 3.8** or newer
* **pip** (Python's package installer)
* **Git** (for cloning the repository)

## 2. Initial Setup

Follow these steps to get the application code and its dependencies set up.

### Step 2.1: Get the Code
Clone the repository from your source control or download and extract the project files into a directory on your computer.

```bash
# Example using Git
git clone <your-repository-url>
cd <project-directory>
```

### Step 2.2: Create a Virtual Environment
It is highly recommended to use a virtual environment to manage project-specific dependencies.

```bash
# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS and Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

### Step 2.3: Install Dependencies
Install all the required Python libraries using the `requirements.txt` file.

```bash
pip install -r requirements.txt
```

## 3. Configuration

The application is configured using environment variables. A template is provided for you.

1.  **Create a `.env` file:** Copy the example configuration file.
    ```bash
    cp .env.example .env
    ```
2.  **Edit the `.env` file:** Open the new `.env` file in a text editor and fill in the required values.

### Required Settings:
* `SECRET_KEY`: **This is critical for security.** Generate a long, random string for this value. You can use an online generator or a command like `openssl rand -hex 32`.
* `DATABASE_URL`: By default, this is set to use a local SQLite database (`app.db`), which will be created automatically. No changes are needed unless you want to use a different database like PostgreSQL.
* `LDAP_SERVER`, `LDAP_BASE_DN`, etc.: Fill in all the connection details for your LDAP server. The `LDAP_BIND_DN` user needs read access to the directory and write access if you intend to use the "Add Company" or "Edit Person" features.

### Optional Settings:
* **Authentication Methods:**
    * `ENABLE_LOCAL_LOGIN`: Set to `False` to hide the "Local Account" tab on the login page.
    * `ENABLE_LDAP_LOGIN`: Set to `False` to hide the "LDAP" tab on the login page.
* **SSO Providers:** To enable an SSO provider (Google, Keycloak, Authentik), you must fill in its `CLIENT_ID` and `CLIENT_SECRET` variables. If these are left blank, the corresponding button will not appear on the login page. Refer to the specific `README.md` file for each provider for setup instructions.
* **Attribute Maps:** Customize `LDAP_ATTRIBUTE_MAP` and `LDAP_COMPANY_ATTRIBUTE_MAP` to control which fields are displayed throughout the application.

## 4. Running the Application

### Development Mode
For development and testing, you can use Flask's built-in web server.

1.  Ensure your virtual environment is activated.
2.  Run the following command:
    ```bash
    flask run
    ```
3.  Open your web browser and navigate to `http://127.0.0.1:5000`.

**Note:** This mode is **not suitable for production**. It is slow and insecure.

### Production Mode
For a production deployment, you must use a proper WSGI server like Gunicorn.

1.  Ensure your virtual environment is activated.
2.  Run the application using Gunicorn, binding it to a network interface.
    ```bash
    # This will serve the application on port 8000 on all network interfaces
    gunicorn --bind 0.0.0.0:8000 wsgi:application
    ```
3.  You would typically run this behind a reverse proxy like Nginx or Caddy for SSL termination and improved performance.

## 5. First Login (Local Admin)

If you have `ENABLE_LOCAL_LOGIN` set to `True`, the application will automatically create a default administrator account the first time it starts.

* **Username:** `admin`
* **Password:** `changeme`

When you log in with these credentials for the first time, you will be **forced to reset your password** before you can access any other part of the application. Once you've reset the password, you can use the admin page to manage other local users.

## 6. Handling Database Schema Updates

This application uses a simple SQLite database (`app.db`) for local user management. The database file is created automatically if it doesn't exist.

If a future update to the application includes changes to the database schema (e.g., adding a new column to the `User` table), you will need to recreate the database.

1.  **Stop the application.**
2.  **Back up the old database:** Rename or move the existing `app.db` file in the root of your project directory. For example:
    ```bash
    mv app.db app.db.bak
    ```
3.  **Restart the application:**
    ```bash
    # For development:
    flask run
    # For production:
    gunicorn --bind 0.0.0.0:8000 wsgi:application
    ```

When the application starts, it will not find an `app.db` file and will automatically create a new one with the updated schema.

**Important:** This process will delete all existing local user accounts. The default `admin` user will be re-created, and you will need to log in with the password `changeme` and reset it again.

