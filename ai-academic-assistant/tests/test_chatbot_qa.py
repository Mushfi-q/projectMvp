"""
QA Script: 20 Manual AI Test Cases
===================================
Instructions: Run these exact prompts against the AI Academic Assistant Chatbot manually.
Verify the robustness, tone, and accuracy of the output in a conversational tone.

Category 1: Conceptual Inquiries (RAG / Data Retrieval)
-------------------------------------------------------
1. "What is the primary difference between Supervised and Unsupervised Learning?"
2. "Explain the architecture of a Convolutional Neural Network."
3. "Detail the concept of Overfitting in Machine Learning."
4. "What are the common techniques for data normalization?"
5. "Can you summarize the Backpropagation algorithm in simple terms?"

Category 2: Performance Checks (Database Integrations - Marks / Attendance)
-------------------------------------------------------------------------
6. "Am I failing this subject?"
7. "What is my current attendance percentage for this class?"
8. "Have I missed any assignments in this course?"
9. "What was my score on the last internal exam?"
10. "Given my current grades, how much do I need to score on the final to pass?"

Category 3: Deadline Constraints (Assignment Tracking)
------------------------------------------------------
11. "Are there any pending assignments due this week?"
12. "When is the next deadline?"
13. "What assignments have I already submitted?"
14. "Is anything due tomorrow?"
15. "Prioritize my study schedule based on upcoming assignment weights."

Category 4: Custom Reminder Executions (NLP Entity Extraction)
--------------------------------------------------------------
16. "Remind me to study Machine Learning tonight at 8 PM."
17. "Set a reminder for my assignment deadline tomorrow at 9 AM."
18. "Schedule a reminder to review Neural Networks on Friday at 5 PM."
19. "Remind me to check my attendance status next Monday at 10 AM."
20. "Remind me about the Midterm Exam on October 15th at 8:00 AM."

"""

# Usage Script to programmatically map tests (Implementation coming soon)
TEST_MATRIX = {
    "Conceptual": [
        "What is the primary difference between Supervised and Unsupervised Learning?",
        "Explain the architecture of a Convolutional Neural Network.",
        "Detail the concept of Overfitting in Machine Learning.",
        "What are the common techniques for data normalization?",
        "Can you summarize the Backpropagation algorithm in simple terms?"
    ],
    "Performance": [
        "Am I failing this subject?",
        "What is my current attendance percentage for this class?",
        "Have I missed any assignments in this course?",
        "What was my score on the last internal exam?",
        "Given my current grades, how much do I need to score on the final to pass?"
    ],
    "Deadline": [
        "Are there any pending assignments due this week?",
        "When is the next deadline?",
        "What assignments have I already submitted?",
        "Is anything due tomorrow?",
        "Prioritize my study schedule based on upcoming assignment weights."
    ],
    "Reminder": [
        "Remind me to study Machine Learning tonight at 8 PM.",
        "Set a reminder for my assignment deadline tomorrow at 9 AM.",
        "Schedule a reminder to review Neural Networks on Friday at 5 PM.",
        "Remind me to check my attendance status next Monday at 10 AM.",
        "Remind me about the Midterm Exam on October 15th at 8:00 AM."
    ]
}

def print_test_plan():
    print("AI Chatbot QA Script \n" + "="*20)
    for category, questions in TEST_MATRIX.items():
        print(f"\n[ {category} Checks ]")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. \"{q}\"")

if __name__ == "__main__":
    print_test_plan()
