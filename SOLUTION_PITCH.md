# Adhikar — Making Government Welfare More Accessible Through Voice AI

**Challenge:** Great Indian AI Internship Challenge by Gnani AI

**Live Demo:** https://www.get-adhikar.vercel.app  
**GitHub:** https://github.com/0Curious0/adhikar

## The Problem

India has numerous government welfare schemes, but discovering relevant schemes, understanding eligibility and navigating application or grievance procedures can be difficult. Language barriers, limited literacy and complicated digital portals make accessing these benefits even harder.

**The challenge isn't just making welfare schemes available; it's making them accessible.**

## The Solution

**Adhikar is a voice-first, multilingual citizen assistance platform that helps people discover government welfare schemes, check eligibility and understand benefit-related grievance procedures through natural conversations.**

Users can describe their circumstances through voice or text instead of navigating lengthy documents or complicated portals.

Adhikar supports **10 Indian languages:** Hindi, English, Bengali, Gujarati, Kannada, Malayalam, Marathi, Punjabi, Tamil and Telugu.

## How It Works

Adhikar follows four steps:

1. **Discover:** Identify relevant schemes based on the user's circumstances.
2. **Verify:** Ask follow-up questions and evaluate eligibility.
3. **Understand:** Explain benefits, eligibility conditions, required documents and grievance procedures.
4. **Act:** Provide next-step guidance and help prepare grievance or complaint drafts.

Users can switch between schemes naturally and track individual enquiries through their activity history.

The current knowledge base covers widow pension schemes, PM-KISAN, Ayushman Bharat PM-JAY and the Public Distribution System (PDS).

## Technology and Engineering

- **Gnani AI Prisma v2.5:** Speech-to-text.
- **Gnani AI Timbre v2.5:** Text-to-speech.
- **Sarvam Prism:** Intent and scheme classification.
- **Sarvam 105B:** Entity extraction.
- **Sarvam 105B Conversations:** Conversational responses.

**Backend:** Python, FastAPI  
**Frontend:** React, TypeScript

A key engineering decision is that **eligibility is computed, not generated.** Language models extract information and communicate results, while a deterministic, rule-based evaluator checks user information against structured scheme criteria. This keeps eligibility decisions separate from LLM-generated responses.

## Expected Impact

Adhikar aims to reduce language, literacy and information barriers between citizens and government welfare services. By making scheme discovery and eligibility guidance conversational, it can make essential public-service information more accessible and understandable.

**Adhikar — Your rights. Your entitlements. Made accessible.**