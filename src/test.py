"""
Quick test script to verify You.com API is working
Run: python test_you_api.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_you_api():
    """Test if You.com API is working"""
    
    # Get API key
    YOU_API_KEY = os.getenv("YOU_API_KEY", "")
    
    print("=" * 60)
    print("🧪 TESTING YOU.COM API")
    print("=" * 60)
    
    # Check if API key exists
    if not YOU_API_KEY:
        print("❌ ERROR: YOU_API_KEY not found in .env file")
        print("\nAdd this to your .env file:")
        print("YOU_API_KEY=your_actual_api_key_here")
        return False
    
    print(f"✅ API Key found: {YOU_API_KEY[:10]}...{YOU_API_KEY[-4:]}")
    print()
    
    # Test query
    test_query = "GDPR data breach notification requirements"
    print(f"🔍 Testing search: '{test_query}'")
    print()
    
    try:
        # Make API call
        headers = {"X-API-Key": YOU_API_KEY}
        params = {
            "query": test_query,
            "num_web_results": 3
        }
        
        print("📡 Calling You.com API...")
        response = requests.get(
            "https://api.ydc-index.io/search",
            headers=headers,
            params=params,
            timeout=10
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", [])
            
            if hits:
                print(f"✅ SUCCESS! Found {len(hits)} results")
                print()
                print("=" * 60)
                print("📋 RESULTS:")
                print("=" * 60)
                
                for i, hit in enumerate(hits, 1):
                    print(f"\n{i}. {hit.get('title', 'No title')}")
                    print(f"   URL: {hit.get('url', 'No URL')}")
                    print(f"   Snippet: {hit.get('description', 'No description')[:150]}...")
                
                print()
                print("=" * 60)
                print("✅ YOU.COM API IS WORKING PERFECTLY!")
                print("=" * 60)
                return True
            else:
                print("⚠️ WARNING: API responded but returned no results")
                print("Response:", response.text[:500])
                return False
                
        elif response.status_code == 401:
            print("❌ ERROR: Invalid API Key (401 Unauthorized)")
            print("Check your YOU_API_KEY in .env file")
            return False
            
        elif response.status_code == 429:
            print("⚠️ ERROR: Rate limit exceeded (429)")
            print("Wait a few minutes and try again")
            return False
            
        else:
            print(f"❌ ERROR: Unexpected status code {response.status_code}")
            print("Response:", response.text[:500])
            return False
            
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timeout")
        print("You.com API took too long to respond")
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Connection failed")
        print("Check your internet connection")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_you_api()
    
    if success:
        print("\n✅ Next step: Test with your RAG system")
        print("Ask a question like: 'What are recent GDPR enforcement cases?'")
    else:
        print("\n❌ Fix the issues above before proceeding")