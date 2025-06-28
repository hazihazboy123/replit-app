# Simplified Vignette Format for N8N

## New Structure

Your vignette should now have this simplified structure:

```json
{
  "vignette": {
    "clinical_case": "A 45-year-old patient presents with arm weakness after trauma. Which spinal segment is most likely affected? A. C1-C3 B. C4-T1 C. T2-T5 D. T1-T4 E. L1-L3 Correct Answer: B. C4-T1",
    "explanation": "The cervical enlargement (C4-T1) contains motor neurons that innervate the upper extremities. Damage to this region results in arm weakness and sensory loss."
  }
}
```

## What Each Field Does

1. **clinical_case**: Complete scenario including patient presentation, question, choices (A, B, C, D, E), and correct answer
2. **explanation**: Educational explanation of why the answer is correct

## Final Display Format

This will display as:
```
A 45-year-old patient presents with arm weakness after trauma. Which spinal segment is most likely affected?

A. C1-C3
B. C4-T1  
C. T2-T5
D. T1-T4
E. L1-L3

Correct Answer: B. C4-T1

Explanation:
The cervical enlargement (C4-T1) contains motor neurons that innervate the upper extremities. Damage to this region results in arm weakness and sensory loss.
```

Perfect for medical education!