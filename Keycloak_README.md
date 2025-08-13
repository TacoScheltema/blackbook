# Configuring Keycloak for Single Sign-On (SSO)

This guide provides step-by-step instructions for setting up Keycloak as an SSO provider for the Flask Address Book application. The process involves creating and configuring a client within your Keycloak realm.

## Step 1: Navigate to Your Keycloak Realm

1.  **Log in to Keycloak:** Open your Keycloak admin console.
2.  **Select Your Realm:** From the dropdown in the top-left corner, choose the realm you want to use for authentication (e.g., `master` or a custom realm you've created).

## Step 2: Create a New Client

A "client" in Keycloak is what represents your application.

1.  **Go to Clients:** In the left-hand navigation menu, click on **Clients**.
2.  **Create a New Client:** On the clients page, click the **Create** button.
3.  **Configure the Client:**
    * **Client ID:** Enter a unique ID for your application, for example, `flask-address-book`.
    * **Client Protocol:** Ensure `openid-connect` is selected.
    * **Root URL:** Leave this blank for now.
4.  **Save:** Click **Save**.

## Step 3: Configure Client Settings

After creating the client, you'll be taken to its configuration page.

1.  **Access Type:** Change the **Access Type** from `public` to `confidential`. This is a critical step for secure server-side applications.
2.  **Valid Redirect URIs:** This is the most important setting. You must tell Keycloak where it is allowed to send users back to after they log in. In the **Valid Redirect URIs** field, enter the callback URL for your application, replacing `http://localhost:5000` with your application's actual URL.
    ```
    http://localhost:5000/authorize/keycloak
    ```
3.  **Save:** Scroll to the bottom and click **Save**.

## Step 4: Get Your Credentials

Now that the client is configured, you can retrieve the credentials your Flask application needs.

1.  **Go to the Credentials Tab:** Near the top of the client configuration page, click on the **Credentials** tab.
2.  **Find the Secret:** You will see a field labeled **Secret**. This is your **Client Secret**. Copy this value.

## Step 5: Configure the Flask Application

Finally, update the `.env` file in your Flask application's root directory with the credentials from Keycloak.

1.  **Open `.env` file:** Open the `.env` file in your text editor.
2.  **Fill in the Keycloak variables:** Find the `KEYCLOAK` section and paste the values.

    ```dotenv
    # Keycloak
    KEYCLOAK_CLIENT_ID="flask-address-book"
    KEYCLOAK_CLIENT_SECRET="<PASTE YOUR CLIENT SECRET HERE>"
    KEYCLOAK_SERVER_URL="[https://keycloak.yourdomain.com/auth/realms/your-realm](https://keycloak.yourdomain.com/auth/realms/your-realm)"
    ```
    **Important:**
    * Replace `KEYCLOAK_CLIENT_ID` with the ID you chose in Step 2.
    * Replace `KEYCLOAK_SERVER_URL` with the full URL to your Keycloak realm's endpoint.

3.  **Restart the Application:** Stop and restart your Flask application for the new environment variables to be loaded.

You should now see a "Sign In with Keycloak" button on your login page, which will correctly redirect users to your Keycloak server for authentication.

