### welcome_assignment_answers
### Input - All nine questions given in the assignment.
### Output - The right answer for the specific question.

def welcome_assignment_answers(question):
    """
    Returns answers to security and networking fundamentals questions.
    
    Args:
        question: A string containing one of the predefined questions
        
    Returns:
        answer: A string containing the answer to the question
    """
    
    # Question 1: Slack passphrase
    if question == "In Slack, what is the secret passphrase posted in the #lab-python-getting-started channel posted by a TA?":
        answer = "pcap"
    
    # Question 2: Encoding vs Encryption
    elif question == "Are encoding and encryption the same? - Yes/No":
        # Encryption is reversible transformation that requires a key for security
        # They serve different purposes, so they are NOT the same
        answer = "No"
    
    # Question 3: Decrypt without key
    elif question == "Is it possible to decrypt a message without a key? - Yes/No":
        # Decryption by definition requires the appropriate key
        answer = "No"
    
    # Question 4: Decode without key
    elif question == "Is it possible to decode a message without a key? - Yes/No":
        # Encoding/decoding is for data representation, not security and doesn't require a key
        answer = "Yes"
    
    # Question 5: Hashed message reversibility
    elif question == "Is a hashed message supposed to be un-hashed? - Yes/No":
        # Hashing is a one-way function by design, 
        # It's meant to be irreversible for security purposes
        answer = "No"
    
    # Question 6: SHA256 of NYU email
    elif question == "What is the SHA256 hashing value of your NYU email and use the answer in your code - ":
        # import hashlib
        # email = "mb10812@nyu.edu"        
        answer = "54bcc73d4788726cfbfe2ab8a9c7c3620198d5859382256bdc2299fa81c39ce1"
    
    # Question 7: MD5 security
    elif question == "Is MD5 a secured hashing algorithm? - Yes/No":
        # MD5 is cryptographically broken and unsuitable for security purposes
        # It has known collision vulnerabilities
        answer = "No"
    
    # Question 8: DNS layer
    elif question == "What layer of the TCP/IP model does the protocol DNS belong to? - The answer should be an integer number":
        # TCP/IP Model layers: 1=Link, 2=Internet, 3=Transport, 4=Application
        # DNS operates at the Application layer
        answer = 5
    
    # Question 9: ICMP layer
    elif question == "What layer of the TCP/IP model does the protocol ICMP belong to? - The answer should be an integer number":
        # ICMP (Internet Control Message Protocol) operates at the Internet layer
        answer = 3
    
    else:
        # Error handling for invalid/mistyped questions
        # This catches typos or questions not in the expected format
        answer = "This is not my beautiful wife! This is not my beautiful car! How did I get here?"
    
    return answer


# Helper function to generate SHA256 hash for NYU email
def generate_sha256_hash(email):
    """
    Generates SHA256 hash of the given email.
    Use this to get the answer for Question 6.
    """
    import hashlib
    return hashlib.sha256(email.encode()).hexdigest()


if __name__ == "__main__":
    # Debug and verify the program works
    print("Testing all questions:\n")
    
    # List of all questions
    questions = [
        "In Slack, what is the secret passphrase posted in the #lab-python-getting-started channel posted by a TA?",
        "Are encoding and encryption the same? - Yes/No",
        "Is it possible to decrypt a message without a key? - Yes/No",
        "Is it possible to decode a message without a key? - Yes/No",
        "Is a hashed message supposed to be un-hashed? - Yes/No",
        "What is the SHA256 hashing value of your NYU email and use the answer in your code - ",
        "Is MD5 a secured hashing algorithm? - Yes/No",
        "What layer of the TCP/IP model does the protocol DNS belong to? - The answer should be an integer number",
        "What layer of the TCP/IP model does the protocol ICMP belong to? - The answer should be an integer number"
    ]
    
    # Test each question
    for i, q in enumerate(questions, 1):
        print(f"Q{i}: {q}")
        print(f"A{i}: {welcome_assignment_answers(q)}\n")
    
    # Test error handling
    print("Testing error handling:")
    print(welcome_assignment_answers("This is a typo question"))
    
    # Helper to generate SHA256 hash if needed
    print("\n" + "="*50)
    print("SHA256 Hash Generator (Optional)")
    print("="*50)
    your_email = input("Enter your NYU email (or press Enter to skip): ")
    if your_email:
        hash_value = generate_sha256_hash(your_email)

        print(f"\nYour SHA256 hash: {hash_value}")







