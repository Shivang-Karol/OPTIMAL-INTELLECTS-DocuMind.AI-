"""
Test Script for Chat History & Summarization Features
======================================================
Run this script to test the new features without a frontend.
"""

import requests
import json
import time

API_BASE = "http://localhost:8000/api/v1/hackrx"

def test_chat_session():
    """Test creating a chat session and asking questions."""
    print("\n" + "="*60)
    print("TEST 1: Creating Chat Session")
    print("="*60)
    
    # Test data
    payload = {
        "documents": "https://hackrx.blob.core.windows.net/hackrx/rounds/FinalRound4SubmissionPDF.pdf",
        "questions": [
            "What is this document about?",
            "What are the key topics covered?"
        ]
    }
    
    print(f"\n📤 Sending request with {len(payload['questions'])} questions...")
    
    response = requests.post(f"{API_BASE}/run", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success!")
        print(f"📝 Session ID: {data['session_id']}")
        print(f"\n💬 Answers:")
        for i, answer in enumerate(data['answers'], 1):
            print(f"  {i}. {answer[:100]}...")
        return data['session_id']
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        return None

def test_get_history(session_id):
    """Test retrieving chat history."""
    print("\n" + "="*60)
    print("TEST 2: Retrieving Chat History")
    print("="*60)
    
    payload = {"session_id": session_id}
    
    print(f"\n📤 Fetching history for session: {session_id}")
    
    response = requests.post(f"{API_BASE}/history", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success!")
        print(f"📊 Total messages: {data['total_messages']}")
        print(f"\n📜 History:")
        for i, item in enumerate(data['history'], 1):
            print(f"\n  Message {i}:")
            print(f"    Q: {item['question']}")
            print(f"    A: {item['answer'][:80]}...")
            print(f"    Time: {item['timestamp']}")
        return True
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        return False

def test_list_sessions():
    """Test listing all sessions."""
    print("\n" + "="*60)
    print("TEST 3: Listing All Sessions")
    print("="*60)
    
    print(f"\n📤 Fetching all sessions...")
    
    response = requests.get(f"{API_BASE}/sessions")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success!")
        print(f"📊 Total sessions: {data['total_sessions']}")
        print(f"\n📋 Sessions:")
        for i, session in enumerate(data['sessions'][:5], 1):  # Show first 5
            print(f"\n  {i}. Session ID: {session['session_id']}")
            print(f"     Preview: {session['first_message'][:60]}...")
            print(f"     Messages: {session['message_count']}")
            print(f"     Last active: {session['last_timestamp']}")
        return True
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        return False

def test_summarize(session_id, use_granite=False):
    """Test session summarization."""
    print("\n" + "="*60)
    print(f"TEST 4: Summarizing Session ({'Granite' if use_granite else 'GPT'})")
    print("="*60)
    
    payload = {
        "session_id": session_id,
        "use_granite": use_granite
    }
    
    print(f"\n📤 Requesting summary with {'IBM Granite' if use_granite else 'GPT-4o-mini'}...")
    
    response = requests.post(f"{API_BASE}/summarize", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Success!")
        print(f"🤖 Model used: {data['model_used']}")
        print(f"📊 Total messages: {data['total_messages']}")
        print(f"\n📝 Summary:")
        print(f"   {data['summary']}")
        print(f"\n🔑 Key Points:")
        for i, point in enumerate(data['key_points'], 1):
            print(f"   {i}. {point}")
        return True
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)
        return False

def run_all_tests():
    """Run all tests in sequence."""
    print("\n" + "🚀"*30)
    print("CHAT HISTORY & SUMMARIZATION FEATURE TESTS")
    print("🚀"*30)
    
    # Test 1: Create session
    session_id = test_chat_session()
    
    if not session_id:
        print("\n❌ Session creation failed. Aborting tests.")
        return
    
    # Wait a bit for MongoDB to sync
    time.sleep(1)
    
    # Test 2: Get history
    test_get_history(session_id)
    
    # Test 3: List all sessions
    test_list_sessions()
    
    # Test 4: Summarize with GPT
    test_summarize(session_id, use_granite=False)
    
    # Test 5: Summarize with Granite (if configured)
    print("\n" + "="*60)
    print("💡 TIP: To test IBM Granite, set up credentials in .env")
    print("   See IBM_GRANITE_SETUP.md for instructions")
    print("="*60)
    
    # Optionally test Granite
    try_granite = input("\nWould you like to test IBM Granite? (y/n): ").lower()
    if try_granite == 'y':
        test_summarize(session_id, use_granite=True)
    
    print("\n" + "✨"*30)
    print("ALL TESTS COMPLETED!")
    print("✨"*30)
    print(f"\n📋 Test Summary:")
    print(f"   Session ID: {session_id}")
    print(f"   API Base: {API_BASE}")
    print(f"\n💡 Next Steps:")
    print(f"   1. Test from frontend/Postman")
    print(f"   2. Set up IBM Granite (optional)")
    print(f"   3. Deploy to production")
    print("\n")

if __name__ == "__main__":
    print("\n⚠️  Make sure the server is running!")
    print("   Run: uvicorn log:app --reload --host 0.0.0.0 --port 8000\n")
    
    proceed = input("Is the server running? (y/n): ").lower()
    
    if proceed == 'y':
        run_all_tests()
    else:
        print("\n👉 Start the server first, then run this script again.")
