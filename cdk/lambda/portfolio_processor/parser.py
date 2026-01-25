import re
from decimal import Decimal
from typing import Dict, Any, List, Optional

"""
Portfolio Parser Module

ASSUMPTIONS ABOUT OUTPUT FORMAT:
1. Market context appears after "StockBot here" greeting and before first stock entry
2. Stock entries are numbered sequentially (1., 2., 3., etc.)
3. Each stock follows format: **NUMBER. SYMBOL** (rules) - **$AMOUNT invested** / $PRICE per share = **SHARES shares**
4. Rationale paragraph follows immediately after the investment math
5. Running totals appear as "**Running Total: $X**" between stocks (optional, used for validation)
6. Portfolio summary section starts with "**PORTFOLIO SUMMARY**"
7. Summary contains:
   - "**Sectors Covered:**" with bullet points like "- Technology: 42.5%"
   - "**Risk Balance:**" with bullet points like "- Large-cap stable: 52%"
8. Markdown bold formatting (** **) may or may not be present in various sections
9. Stock symbols are always UPPERCASE letters

DATA TYPES:
- All numeric values (prices, shares, percentages) are returned as Decimal types
- This ensures DynamoDB compatibility without requiring conversion downstream
- String values and integers remain their native types

ERROR HANDLING STRATEGY:
- Each parsing function returns a sensible default if it fails (empty dict/list/string)
- Stock entry parsing failures are logged but don't stop overall parsing
- Missing fields in a stock entry result in that field being omitted (not None)
- The main parse_portfolio function always returns a valid structure with whatever it could extract
"""


def extract_market_context(raw_output: str) -> str:
    """
    Extract market context/summary from the AI output.

    Assumption: Context appears after "StockBot here" and before the first stock entry
    Format: Any text between greeting and "If I were" or "1." or "**1."

    Args:
        raw_output: Full AI response text

    Returns:
        str: Market context summary, or default message if extraction fails
    """
    try:
        # Match text after "StockBot here" (with optional emoji) up to first stock entry
        pattern = r"(?:StockBot here[^\n]*)\s+(.*?)\s+(?:If I were|(?:\*\*)?1\.)"
        match = re.search(pattern, raw_output, re.DOTALL | re.IGNORECASE)
        if match:
            context = match.group(1).strip()
            # Remove markdown bold formatting if present
            context = re.sub(r'\*\*', '', context)
            if context:  # Only return if non-empty
                return context
    except Exception as e:
        print(f"[PARSER WARNING] Could not extract market context: {e}")

    return "Market context not available"


def parse_stock_entry(entry_text: str, index: int) -> Optional[Dict[str, Any]]:
    """
    Parse a single stock entry from the AI output.

    Assumptions:
    - Entry starts with: **NUMBER. SYMBOL** or NUMBER. SYMBOL
    - Rules appear in parentheses: (rule1, rule2, confidence => investment level)
    - Investment format: **$AMOUNT invested** / $PRICE per share = **SHARES shares**
    - Rationale is the paragraph after the math line
    - Bold markdown (** **) may or may not be present

    Returns None if symbol cannot be extracted (critical failure)
    Returns partial dict if optional fields are missing

    Args:
        entry_text: Raw text for one stock
        index: Stock number (1-based)

    Returns:
        dict: Parsed stock data with available fields, or None if symbol missing
    """
    try:
        stock_data = {"position_number": index}

        # Extract symbol - CRITICAL: must succeed or return None
        # Match: **1. NVDA** or 1. NVDA or **1. NVDA or 1. NVDA**
        symbol_match = re.search(r"^\*?\*?\d+\.\s+([A-Z]+)\*?\*?", entry_text)
        if not symbol_match:
            print(f"[PARSER WARNING] No symbol found in entry {index}")
            return None
        stock_data["symbol"] = symbol_match.group(1)

        # Extract rules cited - OPTIONAL
        try:
            rules_match = re.search(r"\(([^)]+)\)", entry_text)
            if rules_match:
                rules_text = rules_match.group(1)
                # Split by commas, but keep "X => Y" together
                rules_list = [r.strip() for r in re.split(r',\s*(?![^=]*=>)', rules_text)]
                stock_data["rules_cited"] = rules_list
        except Exception as e:
            print(f"[PARSER WARNING] Could not extract rules for {stock_data['symbol']}: {e}")

        # Extract investment amount - OPTIONAL but expected
        try:
            investment_match = re.search(
                r"\$\*?\*?([\d,]+(?:\.\d{2})?)\*?\*?\s+invested", entry_text
            )
            if investment_match:
                stock_data["investment_amount"] = Decimal(
                    investment_match.group(1).replace(",", "")
                )
        except Exception as e:
            print(f"[PARSER WARNING] Could not extract investment for {stock_data['symbol']}: {e}")

        # Extract price per share - OPTIONAL but expected
        try:
            price_match = re.search(
                r"/\s+\$\*?\*?([\d,]+(?:\.\d{2})?)\*?\*?\s+per share", entry_text
            )
            if price_match:
                stock_data["current_price"] = Decimal(price_match.group(1).replace(",", ""))
        except Exception as e:
            print(f"[PARSER WARNING] Could not extract price for {stock_data['symbol']}: {e}")

        # Extract number of shares - OPTIONAL but expected
        try:
            shares_match = re.search(
                r"=\s+\*?\*?([\d,]+(?:\.\d+)?)\*?\*?\s+shares?", entry_text
            )
            if shares_match:
                stock_data["shares"] = Decimal(shares_match.group(1).replace(",", ""))
        except Exception as e:
            print(f"[PARSER WARNING] Could not extract shares for {stock_data['symbol']}: {e}")

        # Extract rationale - OPTIONAL
        # Assumption: Rationale is text after the "shares" line until next stock or section
        try:
            rationale_match = re.search(
                r"shares?\*?\*?\s+(.+?)(?=\n\*?\*?\d+\.|$|\*\*PORTFOLIO SUMMARY)",
                entry_text,
                re.DOTALL,
            )
            if rationale_match:
                rationale = rationale_match.group(1).strip()
                # Remove "Running Total" lines if present
                rationale = re.sub(r"\*?\*?Running Total:.*?\*?\*?", "", rationale, flags=re.IGNORECASE).strip()
                # Remove markdown bold
                rationale = re.sub(r'\*\*', '', rationale)
                if rationale:  # Only add if non-empty
                    stock_data["rationale"] = rationale
        except Exception as e:
            print(f"[PARSER WARNING] Could not extract rationale for {stock_data['symbol']}: {e}")

        return stock_data

    except Exception as e:
        print(f"[PARSER WARNING] Unexpected error parsing stock entry {index}: {e}")
        return None


def parse_sectors(raw_output: str) -> Dict[str, float]:
    """
    Parse sector distribution from the summary section.

    Assumption: Format is "**Sectors Covered:**" followed by bullet points
    Example: "- Technology (AI/Software): 42.5% (NVDA, MSFT, ...)"
    Pattern: "- SECTOR_NAME: PERCENTAGE%"

    Args:
        raw_output: Full AI response text

    Returns:
        dict: Sector name -> percentage mapping (empty dict on failure)
    """
    try:
        sectors = {}
        # Find the "Sectors Covered:" section (case insensitive, with/without bold)
        sector_section_match = re.search(
            r"\*?\*?Sectors Covered:\*?\*?\s*(.*?)(?=\*?\*?Risk Balance:|\*?\*?Lesser-Known|$)",
            raw_output,
            re.DOTALL | re.IGNORECASE,
        )

        if sector_section_match:
            sector_text = sector_section_match.group(1)
            # Parse lines like "- Technology (AI/Software): 42.5%"
            # Capture everything before colon as sector name, then the percentage
            sector_lines = re.findall(
                r"-\s*([^:]+):\s*([\d.]+)%", sector_text, re.IGNORECASE
            )
            for sector_name, percentage in sector_lines:
                sectors[sector_name.strip()] = Decimal(percentage)

        if not sectors:
            print("[PARSER WARNING] No sectors found in output")

        return sectors

    except Exception as e:
        print(f"[PARSER WARNING] Could not parse sectors: {e}")
        return {}


def parse_risk_balance(raw_output: str) -> Dict[str, float]:
    """
    Parse risk balance from the summary section.

    Assumption: Format is "**Risk Balance:**" followed by bullet points
    Example: "- Large-cap stable (NVDA, MSFT, ...): 52% ✓"
    Pattern: "- RISK_CATEGORY (optional stocks list): PERCENTAGE%"

    Args:
        raw_output: Full AI response text

    Returns:
        dict: Risk category -> percentage mapping (empty dict on failure)
    """
    try:
        risk_balance = {}
        # Find the "Risk Balance:" section (case insensitive, with/without bold)
        risk_section_match = re.search(
            r"\*?\*?Risk Balance:\*?\*?\s*(.*?)(?=\*?\*?Lesser-Known|\*?\*?Key Themes:|$)",
            raw_output,
            re.DOTALL | re.IGNORECASE,
        )

        if risk_section_match:
            risk_text = risk_section_match.group(1)
            # Parse lines like "- Large-cap stable (...): 52% ✓"
            # Capture risk category, ignore optional (stock list), capture percentage
            risk_lines = re.findall(
                r"-\s*([^:]+?)(?:\s*\([^)]*\))?\s*:\s*([\d.]+)%", risk_text
            )
            for risk_category, percentage in risk_lines:
                # Clean up category name (remove checkmarks, extra whitespace)
                category = risk_category.strip().rstrip('✓').strip()
                risk_balance[category] = Decimal(percentage)

        if not risk_balance:
            print("[PARSER WARNING] No risk balance found in output")

        return risk_balance

    except Exception as e:
        print(f"[PARSER WARNING] Could not parse risk balance: {e}")
        return {}


def parse_portfolio(raw_output: str) -> Dict[str, Any]:
    """
    Parse the complete AI output into structured portfolio data.

    This is the main entry point. It calls all sub-parsers and assembles
    the final structure. Each sub-parser has its own error handling and
    returns safe defaults, so this function will ALWAYS return a valid
    structure even if parsing partially fails.

    Structure returned:
    {
        "stocks": [list of stock dicts],
        "summary": {
            "stock_count": int,
            "sectors": dict,
            "risk_balance": dict,
            "market_context": str
        }
    }

    Args:
        raw_output: Full AI response text

    Returns:
        dict: Structured portfolio data (always returns valid structure)
    """
    # Initialize with safe defaults
    structured_data = {
        "stocks": [],
        "summary": {
            "stock_count": 0,
            "sectors": {},
            "risk_balance": {},
            "market_context": "Market context not available"
        }
    }

    try:
        # Extract individual stock entries
        # Pattern: Match numbered entries with uppercase symbols
        # Handles both **1. NVDA** and plain 1. NVDA formats
        stock_pattern = r"(\*?\*?\d+\.\s+[A-Z]+\*?\*?.*?)(?=\n\*?\*?\d+\.\s+[A-Z]+|\*\*PORTFOLIO SUMMARY|$)"
        matches = re.finditer(stock_pattern, raw_output, re.DOTALL)

        stocks_parsed = 0
        stocks_failed = 0

        for match in matches:
            stock_entry = match.group(0)
            # Extract position number
            pos_match = re.search(r"^\*?\*?(\d+)\.", stock_entry)
            if pos_match:
                index = int(pos_match.group(1))
                parsed_stock = parse_stock_entry(stock_entry, index)
                if parsed_stock:
                    structured_data["stocks"].append(parsed_stock)
                    stocks_parsed += 1
                else:
                    stocks_failed += 1

        # Build summary (each function has its own error handling)
        structured_data["summary"] = {
            "stock_count": len(structured_data["stocks"]),
            "sectors": parse_sectors(raw_output),
            "risk_balance": parse_risk_balance(raw_output),
            "market_context": extract_market_context(raw_output),
        }

        # Log summary
        print(
            f"[PARSER] Parsing complete: {stocks_parsed} stocks parsed successfully, "
        )

    except Exception as e:
        # This should rarely happen since each sub-parser handles its own errors
        print(f"[PARSER ERROR] Unexpected error in parse_portfolio: {e}")
        # Still return the partial data we have

    return structured_data
