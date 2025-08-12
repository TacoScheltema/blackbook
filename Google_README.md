# Configuring Google for Single Sign-On (SSO)

This guide will walk you through setting up Google as an SSO provider for the Flask Address Book application. This process involves creating a project in the Google Cloud Console, configuring an OAuth consent screen, and generating credentials.

## Step 1: Create a Project in Google Cloud Console

If you don't already have one, you'll need to create a project to hold your application's credentials.

1.  **Go to the Google Cloud Console:** Navigate to [console.cloud.google.com](https://console.cloud.google.com).
2.  **Create a New Project:** Click the project dropdown in the top bar and select **New Project**.
3.  **Name Your Project:** Give it a descriptive name, like `Address Book SSO`, and click **Create**.

## Step 2: Configure the OAuth Consent Screen

This is the screen users will see when they are asked to grant your application access to their Google account information.

1.  **Navigate to APIs & Services:** In the main navigation menu (☰), go to **APIs & Services** -> **OAuth consent screen**.
2.  **Choose User Type:** Select **External** and click **Create**.
3.  **App Information:**
    * **App name:** Enter the name of your application (e.g., `LDAP Address Book`).
    * **User support email:** Select your email address.
    * **Developer contact information:** Enter your email address.
4.  **Save and Continue:** Click **Save and Continue** to proceed.
5.  **Scopes:** You do not need to add any additional scopes for basic authentication. Click **Save and Continue**.
6.  **Test Users:** You can optionally add test users if your app is in testing mode. For now, you can skip this. Click **Save and Continue**.
7.  **Publish the App:** On the summary screen, click **Back to Dashboard**. You may see a button to **Publish App**. Click it and confirm to make your app available to any Google user.

## Step 3: Create OAuth 2.0 Credentials

Now, you will generate the actual credentials your Flask application will use.

1.  **Navigate to Credentials:** In the **APIs & Services** menu, go to **Credentials**.
2.  **Create Credentials:** Click **+ Create Credentials** at the top of the page and select **OAuth client ID**.
3.  **Configure Client ID:**
    * **Application type:** Select **Web application**.
    * **Name:** Give it a name, like `Address Book Web Client`.
    * **Authorized redirect URIs:** This is a critical step. Click **+ ADD URI** and enter the callback URL for your application. Replace `http://localhost:5000` with your application's actual URL.
        ```
        http://localhost:5000/authorize/google
        ```
4.  **Create:** Click **Create**.

## Step 4: Get Your Credentials

A pop-up will appear showing your **Client ID** and **Client Secret**. You will need these for your application's configuration.

## Step 5: Configure the Flask Application

Finally, update the `.env` file in your Flask application's root directory.

1.  **Open `.env` file:** Open the `.env` file in your text editor.
2.  **Fill in the Google variables:** Find the `GOOGLE` section and paste the values you just copied.

    ```dotenv
    # Google
    GOOGLE_CLIENT_ID="<PASTE YOUR CLIENT ID HERE>"
    GOOGLE_CLIENT_SECRET="<PASTE YOUR CLIENT SECRET HERE>"
    ```

3.  **Restart the Application:** Stop and restart your Flask application for the new environment variables to be loaded.

You should now see a "Sign In with Google" button on your login page, which will correctly redirect users to Google for authentication.

