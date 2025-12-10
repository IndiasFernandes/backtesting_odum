# Federated Identity Explained

## What is Federated Identity?

**Federated Identity** is a way to authenticate to Google Cloud **without using service account keys**. Instead, you use credentials from an external identity provider (like AWS, Azure, or an OIDC provider).

Think of it like this:
- **Service Account Key** = A physical key you carry around
- **Federated Identity** = Using your ID card from another organization (AWS, Azure, etc.) to get access

---

## How It Works

### Traditional Authentication (What You're Using Now)

```
Your Application
    ↓
Uses Service Account Key (gcs-service-account.json)
    ↓
Google Cloud Services
```

**Flow:**
1. You have a JSON key file (`gcs-service-account.json`)
2. Application uses this key to authenticate
3. Google Cloud verifies the key and grants access

**Pros:**
- ✅ Simple setup
- ✅ Works immediately
- ✅ Standard method

**Cons:**
- ⚠️ Long-lived credentials (key doesn't expire)
- ⚠️ If key is compromised, access is compromised
- ⚠️ Need to manage key rotation manually

---

### Federated Identity Authentication

```
Your Application (running on AWS/Azure/etc.)
    ↓
Uses AWS/Azure/OIDC credentials
    ↓
Workload Identity Pool (Google Cloud)
    ↓
Google Cloud Services
```

**Flow:**
1. Your application runs on AWS (or Azure, or another cloud)
2. Application uses AWS IAM credentials (temporary, short-lived)
3. Google Cloud Workload Identity Pool verifies AWS credentials
4. Google Cloud issues temporary access tokens
5. Application uses tokens to access GCS

**Pros:**
- ✅ No long-lived keys to manage
- ✅ Credentials rotate automatically
- ✅ More secure (temporary tokens)
- ✅ Works across cloud providers

**Cons:**
- ⚠️ More complex setup
- ⚠️ Requires Workload Identity Pool configuration
- ⚠️ Need external identity provider

---

## Real-World Example

### Scenario: Application Running on AWS EC2

**Without Federated Identity:**
```bash
# You'd need to:
1. Create service account key in GCP
2. Copy key file to AWS EC2 instance
3. Store key securely on EC2
4. Rotate keys manually every 90 days
```

**With Federated Identity:**
```bash
# You can:
1. EC2 instance uses its AWS IAM role (automatic)
2. Google Cloud trusts AWS IAM
3. Temporary tokens issued automatically
4. No keys to manage or rotate
```

---

## When to Use Federated Identity

### ✅ Use Federated Identity When:

1. **Multi-Cloud Setup**
   - Application runs on AWS but needs GCS access
   - Application runs on Azure but needs GCS access

2. **Security Requirements**
   - Need automatic credential rotation
   - Want to avoid long-lived keys
   - Compliance requires short-lived credentials

3. **CI/CD Pipelines**
   - GitHub Actions authenticating to GCS
   - GitLab CI/CD accessing GCS
   - Jenkins pipelines

4. **Kubernetes Clusters**
   - GKE clusters accessing GCS
   - EKS clusters accessing GCS
   - AKS clusters accessing GCS

### ❌ Don't Need Federated Identity When:

1. **Single Cloud (GCP Only)**
   - Everything runs on Google Cloud
   - Service account keys work fine

2. **Simple Applications**
   - Local development
   - Small projects
   - Standard authentication is sufficient

3. **No External Providers**
   - Not using AWS/Azure/OIDC
   - Only using GCP services

---

## How `certs.json` Fits In

The `certs.json` file contains **certificates** that Google Cloud uses to verify tokens from external identity providers.

### Structure of `certs.json`:

```json
{
  "certificate_hash_1": "-----BEGIN CERTIFICATE-----\n...",
  "certificate_hash_2": "-----BEGIN CERTIFICATE-----\n..."
}
```

**What it does:**
- Contains public certificates from identity providers
- Google Cloud uses these to verify tokens
- Each hash corresponds to a certificate
- Certificates are used to validate federated identity tokens

**When you'd use it:**
- Setting up Workload Identity Federation
- Configuring OIDC providers
- Enabling AWS/Azure authentication

---

## Comparison Table

| Aspect | Service Account Key | Federated Identity |
|--------|-------------------|-------------------|
| **Setup Complexity** | Simple | Complex |
| **Credential Type** | Long-lived JSON key | Short-lived tokens |
| **Rotation** | Manual | Automatic |
| **Security** | Good | Better |
| **Multi-Cloud** | No | Yes |
| **Use Case** | Standard GCP apps | Cross-cloud apps |
| **File Used** | `gcs-service-account.json` | `certs.json` |

---

## Your Current Setup

### What You Have:

```
✅ gcs-service-account.json  → Service account key (standard auth)
✅ certs.json                → Certificates (for federated identity, if needed)
```

### What You're Using:

```
GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcs/gcs-service-account.json
```

**This means:**
- ✅ Using **service account authentication** (standard method)
- ✅ `certs.json` is available but **not currently used**
- ✅ This is the **correct setup** for most applications

---

## When You Might Need Federated Identity

### Example 1: AWS Lambda → GCS

If you had a Lambda function on AWS that needed to access GCS:

```python
# Without federated identity (current)
# Need to store service account key in AWS Secrets Manager
# Manage key rotation manually

# With federated identity (future)
# Lambda uses AWS IAM role
# Google Cloud trusts AWS IAM
# Automatic token generation
```

### Example 2: GitHub Actions → GCS

If you wanted GitHub Actions to upload results to GCS:

```yaml
# Without federated identity
# Store service account key as GitHub Secret
# Key doesn't rotate automatically

# With federated identity
# Use GitHub OIDC provider
# Google Cloud trusts GitHub
# Automatic token generation
```

---

## Summary

**Federated Identity** = Using credentials from external providers (AWS, Azure, OIDC) to access Google Cloud, instead of using service account keys.

**Your Setup:**
- ✅ Using **service account keys** (standard, recommended)
- ✅ `certs.json` available for **future use** if needed
- ✅ **No changes needed** unless you move to multi-cloud

**Bottom Line:**
- Federated identity is **more secure** but **more complex**
- For most GCP-only applications, **service account keys are perfect**
- You only need federated identity if you're doing **multi-cloud** or have **specific security requirements**

---

*Your current setup is correct - federated identity is an advanced feature you may not need unless you're doing cross-cloud authentication.*

