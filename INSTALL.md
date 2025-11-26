# **Installation and Setup Guide**

This document provides instructions on how to set up and run the LDAP Address Book application on your local machine.

## **1. Prerequisites**

Before you begin, ensure you have the following installed on your system:

* **Python 3.8** or newer
* **pip** (Python's package installer)
* **Git** (for cloning the repository)

## **2. Initial Setup**

Follow these steps to get the application code and its dependencies set up.

### **Step 2.1: Get the Code**

Clone the repository from your source control or download and extract the project files into a directory on your
computer.

```shell
# Example using Git
git clone <your-repository-url>
cd <project-directory>
```

### **Step 2.2: Create a Virtual Environment**

It is highly recommended to use a virtual environment to manage project-specific dependencies.

```shell
# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS and Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

### **Step 2.3: Install Dependencies**

Install all the required Python libraries using the requirements.txt file.

```shell
pip install -r requirements.txt
```

## **3. Configuration**

The application is configured using environment variables. A template is provided for you.

1. **Create a .env file:** Copy the example configuration file.

```shell
cp env.example .env
```

2. **Edit the .env file:** Open the new .env file in a text editor and fill in the required values.

### **Required Settings:**

* `SECRET_KEY`: **This is critical for security.** Generate a long, random string for this value. You can use an online
  generator or a command like `openssl rand -hex 32`.
* `DATABASE_URL`: By default, this is set to use a local SQLite database (`app.db`). No changes are needed unless you
  want
  to use a different database like PostgreSQL.
* `LDAP_SERVER`, `LDAP_BASE_DN`, etc.: Fill in all the connection details for your LDAP server.

### **Optional Settings:**

* **Authentication Methods:**
    * `ENABLE_LOCAL_LOGIN`: Set to False to hide the "Local Account" tab on the login page.
    * `ENABLE_LDAP_LOGIN`: Set to False to hide the "LDAP" tab on the login page.
* **SSO Providers:** To enable an SSO provider (_Google_, _Keycloak_, _Authentik_), you must fill in its `CLIENT_ID` and
  `CLIENT_SECRET` variables.
* **Attribute Maps:** Customize `LDAP_ATTRIBUTE_MAP` and `LDAP_COMPANY_ATTRIBUTE_MAP` to control which fields are
  displayed.

## **4. Database Initialization and Upgrades**

This application uses **Flask-Migrate** to manage database schema changes.

### **Step 4.1: First-Time Setup**

After you've configured your `.env` file, the application will create the database automatically when it's first started.
If `ENABLE_LOCAL_LOGIN` is set to `True`, a user `admin` will be created with the initial password provided in `ADMIN_INITIAL_PASS`

## **5. Running the Application**

### **Development Mode**

For development and testing, you can use Flask's built-in web server.

```shell
flask run
```

Open your web browser and navigate to http://127.0.0.1:5000.

### **Production Mode**

For a production deployment, use a proper WSGI server like Gunicorn.

```shell
gunicorn --bind 0.0.0.0:8000 wsgi:application
```

## **6. First Login (Local Admin)**

If you have `ENABLE_LOCAL_LOGIN` set to True, you can now log in with the default administrator account.

* **Username:** `admin`
* **Password:** see `ADMIN_INITIAL_PASS` in `.env`

You will be **forced to reset your password** immediately after your first login.
