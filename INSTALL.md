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

After you've configured your `.env` file, you need to initialize the database.
**Run these commands only once** for the initial setup.

1. Ensure your virtual environment is activated
2. Initialize the migration repository (creates a 'migrations' folder)
    ```shell 
    flask db init
    ```
3. Create the first migration script based on the current models
    ```shell 
    flask db migrate -m "Initial migration."
    ```
4. Apply the migration to create the database and its tables
    ```shell
    flask db upgrade
    ```

### **Step 4.2: Creating the Default Admin User**

After initializing the database, you need to create the default admin user. A helper command is available for this.

1. Ensure your virtual environment is activated
2. This will create the user `admin` with the password `changeme`.
    ```shell
    flask create-admin
    ```

### **Step 4.3: Handling Future Schema Updates**

If you pull new code that includes changes to the database models (e.g., a new column is added), you **do not** delete
the database. Instead, you run the following commands to safely upgrade it:

1. Ensure your virtual environment is activated
2. Generate a new migration script that detects the changes
   ```shell
   flask db migrate -m "A short description of the changes."
   ```
3. Apply the changes to your database
   ```shell
   flask db upgrade
   ```

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
* **Password:** `changeme`

You will be **forced to reset your password** immediately after your first login.
