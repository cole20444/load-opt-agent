#!/usr/bin/env python3
"""
Check OpenAI Status
Helps debug OpenAI API issues by checking rate limits, usage, and account status
"""

import os
import sys
import json
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_openai_status():
    """Check OpenAI API status, rate limits, and usage"""
    
    print("🔍 Checking OpenAI API Status")
    print("=" * 50)
    
    # Check if OpenAI is available
    try:
        from openai import OpenAI
        print("✅ OpenAI library is available")
    except ImportError:
        print("❌ OpenAI library not installed")
        return
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded")
    except ImportError:
        print("⚠️ python-dotenv not available, using system environment")
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        print("   Make sure you have a .env file with your API key")
        print("   Current environment variables:")
        for key, value in os.environ.items():
            if 'OPENAI' in key:
                print(f"     {key}: {value[:10]}...{value[-4:] if len(value) > 14 else '***'}")
        return
    
    print(f"✅ API key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Initialize client
    try:
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI client: {e}")
        return
    
    # Test basic API access
    print("\n🧪 Testing API access...")
    try:
        # Try a simple completion to test access
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=5
        )
        print("✅ Basic API access successful")
    except Exception as e:
        print(f"❌ API access failed: {e}")
        return
    
    # Check available models
    print("\n🤖 Checking available models...")
    try:
        models_response = client.models.list()
        available_models = [model.id for model in models_response.data]
        
        # Check our preferred models
        preferred_models = [
            "gpt-4o",
            "gpt-4o-mini", 
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]
        
        print("Available models:")
        for model in preferred_models:
            if model in available_models:
                print(f"  ✅ {model}")
            else:
                print(f"  ❌ {model} (not available)")
        
        # Show other available models
        other_models = [m for m in available_models if m.startswith('gpt-') and m not in preferred_models]
        if other_models:
            print(f"\nOther GPT models available: {', '.join(other_models[:5])}")
            
    except Exception as e:
        print(f"❌ Failed to check models: {e}")
    
    # Check rate limits (this requires a test request)
    print("\n📊 Checking rate limits...")
    try:
        # Make a test request to trigger rate limit headers
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=10
        )
        
        # Note: OpenAI doesn't always return rate limit headers in the response
        # We can only detect them when we hit the limits
        print("✅ Rate limit check completed")
        print("   Note: Rate limits are only visible when you hit them")
        
    except Exception as e:
        error_str = str(e).lower()
        if "rate limit" in error_str:
            print(f"⚠️ Rate limit detected: {e}")
        elif "quota" in error_str:
            print(f"⚠️ Quota exceeded: {e}")
        else:
            print(f"❌ Error during rate limit check: {e}")
    
    # Check billing status
    print("\n💰 Checking billing status...")
    try:
        # Try to get billing info (this might not be available for all accounts)
        billing_response = client.billing.usage()
        print("✅ Billing API accessible")
        print(f"   Usage data available: {billing_response}")
    except Exception as e:
        print(f"⚠️ Billing API not accessible: {e}")
        print("   This is normal for some account types")
    
    # Provide helpful links
    print("\n🔗 Useful OpenAI Links:")
    print("   Rate Limits: https://platform.openai.com/account/rate-limits")
    print("   Usage Dashboard: https://platform.openai.com/usage")
    print("   Billing: https://platform.openai.com/account/billing")
    print("   API Keys: https://platform.openai.com/api-keys")
    
    print("\n💡 Tips:")
    print("   - Rate limits are per model and per time window")
    print("   - TPM = Tokens Per Minute")
    print("   - RPM = Requests Per Minute")
    print("   - Usage data may take time to appear")
    print("   - Check organization settings if using team accounts")

if __name__ == "__main__":
    check_openai_status() 