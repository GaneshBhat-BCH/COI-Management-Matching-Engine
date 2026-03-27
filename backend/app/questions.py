QUESTIONS_DATA = {
  "role": "You are a Legal & Compliance AI Agent specialized in Conflict of Interest (COI) analysis. You must perform strict rule-based legal evaluation using only the provided REFERENCE_POLICIES. No assumptions, inference, or hallucination are allowed.",

  "QUESTIONS_DATA": {
    "global_instructions": {
      "output_only_value": True,
      "no_explanations": True,
      "multiple_values_format": "Ans1,Ans2",
      "missing_value": "NA",
      "yes_no_values": ["Yes", "No"],
      "rules_reference_instruction": "For questions 13, 14, and 15, perform a deep legal analysis using ONLY the rules defined in REFERENCE_POLICIES. Do not hallucinate."
    },
"assumptions": [
  "Scientific advisory board positions do NOT count as executive management positions.",
  "A Co-Founder is considered an executive management position only if they hold an executive title or have operational decision-making authority.",
  "A Co-Founder who is solely a shareholder, advisor, or holds a non-executive or honorary role is NOT considered executive management.",
  "The Executive Position Rule (A3) applies only if the researcher holds or seeks an executive role with material responsibilities."
]

,

    "QUESTIONS": [
      {
        "id": 1,
        "text": "Is the researcher a cofounder in a company outside of BCH?",
        "prompt": "Extract the data from the input and determine whether the researcher is a cofounder in a company outside of BCH. Output Yes or No. If not mentioned, return No."
      },
      {
        "id": 2,
        "text": "What is the researcher’s role(s)/title(s) in the company?",
        "prompt": "Extract the data from the input and identify the researcher’s role(s) or title(s) in the company. If multiple roles exist, return Ans1,Ans2. If not mentioned, return NA."
      },
      {
        "id": 3,
        "text": "Is the company publicly traded or privately held?",
        "prompt": "Extract the data from the input and determine whether the company is publicly traded or privately held. Output Public or Private. If not mentioned, return NA."
      },
      {
        "id": 4,
        "text": "What is the researcher’s equity in the company?",
        "prompt": "Extract the data from the input and identify the researcher’s equity in the company. Normalize to Cash, Stock, StockOptions. If multiple options exist, return them as a comma-separated list (e.g., Stock,StockOptions). If not mentioned, return NA."
      },
      {
        "id": 5,
        "text": "How much will the researcher be compensated in cash from the company annually?",
        "prompt": "Extract the data from the input and identify the annual cash compensation. The result should be ≤ $ 25000 or > $ 25000. If there are no details, return NA."
      },
      {
        "id": 6,
        "text": "How much time/effort does the researcher spend working for the company?",
        "prompt": "Extract the data from the input and identify time or effort spent working for the company. Convert to percentage of FTE. Full-time = 40 hours/week. (Hours / 40) * 100. If >20 return '> 20 %'. If ≤20 return '≤ 20 %'. Return ONLY these values. If not mentioned, return NA."
      },
      {
        "id": 7,
        "text": "Has the company licensed or is it planning to license intellectual property from BCH?",
        "prompt": "Extract the data from the input and determine whether the company has licensed or plans to license intellectual property from BCH. Output Yes or No. If not mentioned, return NA."
      },
      {
        "id": 8,
        "text": "Will BCH receive equity or financial consideration from the company? If so, how much?",
        "prompt": "Extract the data from the input and determine if BCH receives equity ownership percentage, cash payments, milestones, or royalties. Do NOT include costs. If none or not mentioned, return NA."
      },
      {
        "id": 9,
        "text": "Does the researcher have any grants or research projects that relate to the company?",
        "prompt": "Extract the data from the input and determine whether related grants or research projects exist. Output Yes or No. If not mentioned, return NA."
      },
      {
        "id": 10,
        "text": "Is the related research clinical or basic?",
        "prompt": "Extract the data from the input and determine whether the research is Clinical or Basic. If not mentioned, return NA."
      },
      {
        "id": 11,
        "text": "Is the researcher participating in clinical research related to the company’s technology?",
        "prompt": "Extract the data from the input and determine participation in clinical research related to company technology. Output Yes or No. If not mentioned, return NA."
      },
      {
        "id": 12,
        "text": "Is the company seeking to sponsor research at BCH?",
        "prompt": "Extract the data from the input and determine whether the company seeks to sponsor research at BCH. Output Yes or No. If not mentioned, return NA."
      },
      {
        "id": 13,
        "text": "What COI policy applies to this management plan?",
        "prompt": "Identify the applicable COI Policy from REFERENCE_POLICIES. 1. Carefully review if the facts match 'Inventor_Equity_and_Licensing_Conflict_Policy' (Question 7 is Yes) vs other policies. 2. Output ONLY the key name of the policy found in the REFERENCE_POLICIES schema (e.g., HMS_COI_Policy). Do not assume executive authority for Co-Founders unless explicitly stated."
      },
      {
        "id": 14,
        "text": "What COI rule applies to this management plan?",
        "prompt": "Identify the specific Rule Name from the Policy selected in Question 13. \n\nCONSTRAINTS:\n1. Look up the policy in REFERENCE_POLICIES. \n2. Select the EXACT 'Name' value of the applying rule(s) from that policy's 'Rules' list. \n3. CRITICAL: Do NOT hallucinate names like 'Sponsored Research Rule I(b)' or '1(b) Rule'. ONLY use the Name string exactly as it appears in the list.\n4. Output as a comma-separated list."
      },
      {
        "id": 15,
        "text": "Is the researcher petitioning for an exemption from a COI rule?",
        "prompt": "Perform a DEEP SEMANTIC LEGAL SEARCH for any mention of petition, exemption, exception, waiver, rebuttable presumption, or appeal. Output Yes if mentioned, No if explicitly denied, or NA if not referenced."
      },
      {
        "id": 101,
        "text": "Metadata: DATE",
        "prompt": "Extract the primary date mentioned in the document (e.g., effective date, date of signature, or document date). Format as YYYY-MM-DD if possible, otherwise return as found."
      },
      {
        "id": 102,
        "text": "Metadata: DocuSign Envelope ID",
        "prompt": "Extract the DocuSign Envelope ID if present in the document. It usually starts with 'Envelope Id:'. Return ONLY the ID."
      },
      {
        "id": 103,
        "text": "Metadata: FROM",
        "prompt": "Extract the 'FROM' field or identify the primary sender/entity from whom the document originates."
      }
    ],

    "REFERENCE_POLICIES": {
      "HMS_COI_Policy": {
        "Rules": [
          {
            "ID": "HMS-A1",
            "Name": "Clinical Research Rule (formerly the “1(a) Rule”)",
            "Rule": "The individual participates in clinical research involving the company’s technology AND receives equity compensation (stock/options) from a privately held company OR receives cash compensation > $25,000 per year."
          },
          {
            "ID": "HMS-A2",
            "Name": "Research Support Rule (formerly the “1(b) Rule”)",
            "Rule": "The individual receives equity compensation (stock/options) from a privately held company AND the company sponsors or intends to sponsor research conducted in the individual’s laboratory."
          },
          {
            "ID": "HMS-A3",
            "Name": "Executive Position Rule (formerly the “1(c) Rule”)",
            "Rule": "The individual holds an executive role (CEO, COO, CSO, etc.) AND the company is for-profit AND the individual participates in clinical research or receives sponsored research funding. Note: Co-Founders/Advisors without executive title/authority are NOT executive."
          },
          {
            "ID": "HMS-A4",
            "Name": "External Activity Rule (formerly the “1(d) Rule”)",
            "Rule": "The individual holds a fiduciary role (e.g., Board of Directors) in a for-profit company AND participates in clinical research or receives sponsored research funding."
          }
        ]
      },

      "PHS_COI_Policy": {
        "Rules": [
          {
            "ID": "PHS-1",
            "Name": "PHS FCOI Rule",
            "Rule": "Equity in a privately held company related to a PHS-funded research project that requires a management plan."
          }
        ]
      },

      "Inventor_Equity_and_Licensing_Conflict_Policy": {
        "Rules": [
          {
            "ID": "INV-1",
            "Name": "Inventor Equity and Licensing Conflict Policy Rule",
            "Rule": "When an individual has equity in a private company and is the inventor or co-inventor of technology that BCH has licensed or aims to license to that company."
          }
        ]
      },

      "BCH_COI_Policy": {
        "Rules": [
          {
            "ID": "BCH-1",
            "Name": "BCH COI Policy Rule",
            "Rule": "Senior leadership team members (fiduciary roles) in for-profit companies. Includes rebuttable presumption against participation without compelling reasons."
          }
        ]
      }
    }
  }
}


QUESTIONS = QUESTIONS_DATA['QUESTIONS_DATA']['QUESTIONS']
