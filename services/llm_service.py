"""LLM factory, structured output parser, and deterministic fallback extraction service."""

import re
import json
from datetime import date, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pydantic import ValidationError as PydanticValidationError
from config.settings import Settings, get_settings
from models.planner import (
    PlannerResult,
    NormalizedTravelRequest,
)
from utils.logger import logger

MAX_PLANNER_RETRIES = 2


class DemoPlannerExtractor:
    """Deterministic natural-language travel requirement extractor for DEMO_MODE and offline execution."""

    @staticmethod
    def extract(text: str) -> PlannerResult:
        """Parse natural-language travel text deterministically without external LLM calls."""
        lower = text.lower()
        assumptions: List[str] = [
            "[DEMO_MODE] Deterministic pattern extraction utilized (no live LLM credentials required)."
        ]
        warnings: List[str] = []
        conflicts: List[str] = []
        missing_fields: List[str] = []

        # 1. Route extraction (Origin and Destination)
        origin: Optional[str] = None
        destination: Optional[str] = None

        # Pattern: "<origin> se <destination> ... " (Hinglish pattern)
        se_match = re.search(r"([a-zA-Z\s]{2,20}?)\s+se\s+([a-zA-Z\s]{2,20}?)(?:\s+(?:ka|\d+|trip|days|budget)|[\,\.]|$)", text, re.IGNORECASE)
        if se_match:
            origin = se_match.group(1).strip()
            destination = se_match.group(2).strip()

        # English patterns: "from <origin> to <destination>"
        if not origin or not destination:
            from_to_match = re.search(r"from\s+([a-zA-Z\s]{2,20}?)\s+to\s+([a-zA-Z\s]{2,20}?)(?:\s+(?:for|in|\d+|with|on|budget|from)|[\,\.]|$)", text, re.IGNORECASE)
            if from_to_match:
                origin = origin or from_to_match.group(1).strip()
                destination = destination or from_to_match.group(2).strip()

        # Standalone destination pattern: "trip to <dest>" or "<dest> trip"
        if not destination:
            to_match = re.search(r"(?:trip to|travel to|visit|going to)\s+([a-zA-Z\s]{2,20}?)(?:\s+(?:for|in|\d+|with|on|budget|from)|[\,\.]|$)", text, re.IGNORECASE)
            if to_match:
                destination = to_match.group(1).strip()

        invalid_destinations = {
            "day", "days", "week", "weeks", "month", "months", "year", "years",
            "weekend", "road", "round", "business", "family", "solo", "couple",
            "honeymoon", "short", "long", "quick", "future"
        }

        if not destination:
            dest_trip_match = re.search(r"\b([a-zA-Z]{3,20})\s+(?:trip|vacation|tour)", text, re.IGNORECASE)
            if dest_trip_match and dest_trip_match.group(1).lower() not in invalid_destinations:
                destination = dest_trip_match.group(1).strip()

        # Standalone origin pattern: "from <origin>" or "<origin> se"
        if not origin:
            from_match = re.search(r"(?:from|departing|flying from)\s+([a-zA-Z\s]{2,20}?)(?:\s+(?:to|for|in|\d+|with|budget|on)|[\,\.]|$)", text, re.IGNORECASE)
            if from_match:
                origin = from_match.group(1).strip()
            else:
                se_origin_match = re.search(r"([a-zA-Z\s]{2,20}?)\s+se\b", text, re.IGNORECASE)
                if se_origin_match:
                    origin = se_origin_match.group(1).strip()

        # Clean extraneous words from origin/destination
        stop_words = {"trip", "ka", "ki", "ke", "plan", "karo", "for", "the", "a", "an", "days", "budget", "from", "to", "with", "day", "people", "log"}
        if origin:
            words = [w for w in origin.split() if w.lower() not in stop_words]
            origin = " ".join(words).title() if words else None
        if destination:
            words = [w for w in destination.split() if w.lower() not in stop_words]
            destination = " ".join(words).title() if words else None

        # 2. Duration & Dates
        duration: Optional[int] = None
        start_date: Optional[str] = None
        end_date: Optional[str] = None

        dur_match = re.search(r"(\d+)[\s\-]*(?:days|day|din|d|nights|night)", lower)
        if dur_match:
            duration = int(dur_match.group(1))

        # Date extraction YYYY-MM-DD
        dates_found = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if len(dates_found) >= 2:
            start_date = dates_found[0]
            end_date = dates_found[1]
        elif len(dates_found) == 1:
            start_date = dates_found[0]
            if duration:
                try:
                    s_dt = date.fromisoformat(start_date)
                    end_date = (s_dt + timedelta(days=duration)).isoformat()
                except Exception:
                    pass

        # 3. Travelers
        travelers: Optional[int] = None
        if "solo" in lower:
            travelers = 1
        elif "couple" in lower or "honeymoon" in lower:
            travelers = 2
        else:
            traveler_match = re.search(r"(\d+)\s*(?:people|persons|travelers|travellers|log|adults|pax|friends)", lower)
            if traveler_match:
                travelers = int(traveler_match.group(1))
            else:
                for_n_match = re.search(r"(?:for|with)\s+(\d+)\s*(?:people|persons|log)?", lower)
                if for_n_match:
                    travelers = int(for_n_match.group(1))

        # 4. Budget and Currency
        budget: Optional[float] = None
        currency: str = "USD"

        # Lakh pattern (₹1.5 lakh, 1.5 lakh, 2 lakh)
        lakh_match = re.search(r"(?:₹|rs\.?|inr)?\s*([\d\.]+)\s*(?:lakh|lac)", lower)
        if lakh_match:
            budget = float(lakh_match.group(1)) * 100000.0
            currency = "INR"

        # Explicit INR / ₹ without lakh
        if budget is None:
            inr_match = re.search(r"(?:₹|rs\.?|inr)\s*([\d\,]+(?:\.\d+)?)", lower)
            if inr_match:
                cleaned = inr_match.group(1).replace(",", "")
                try:
                    budget = float(cleaned)
                    currency = "INR"
                except ValueError:
                    pass

        # Dollar pattern ($3000, -$500, 3000 usd)
        if budget is None:
            usd_match = re.search(r"(-?)\$\s*([\d\,]+(?:\.\d+)?)", lower)
            if usd_match:
                sign = -1 if usd_match.group(1) == "-" else 1
                cleaned = usd_match.group(2).replace(",", "")
                try:
                    budget = sign * float(cleaned)
                    currency = "USD"
                except ValueError:
                    pass

        # Generic budget pattern ("budget 50000" or "budget -$500" or "budget is 2000 euro")
        if budget is None:
            gen_match = re.search(r"budget\s+(?:is|of|hai)?\s*[\:\=]?\s*(-?)([^\d\s]{1,3})?\s*([\d\,]+(?:\.\d+)?)", lower)
            if gen_match:
                sign = -1 if gen_match.group(1) == "-" else 1
                curr_symbol = gen_match.group(2) or ""
                val_str = gen_match.group(3).replace(",", "")
                try:
                    budget = sign * float(val_str)
                    if "₹" in curr_symbol or "rs" in curr_symbol:
                        currency = "INR"
                    elif "€" in curr_symbol or "eur" in lower:
                        currency = "EUR"
                    elif "£" in curr_symbol or "gbp" in lower:
                        currency = "GBP"
                    elif "¥" in curr_symbol or "jpy" in lower:
                        currency = "JPY"
                except ValueError:
                    pass

        # Currency detection keywords if not already matched
        if "inr" in lower or "rupee" in lower or "rupees" in lower:
            currency = "INR"
        elif "eur" in lower or "euro" in lower:
            currency = "EUR"
        elif "gbp" in lower or "pound" in lower:
            currency = "GBP"
        elif "jpy" in lower or "yen" in lower:
            currency = "JPY"

        # 5. Interests
        interests: List[str] = []
        interest_keywords = [
            "food", "culture", "nature", "adventure", "shopping", "history",
            "nightlife", "relaxation", "beach", "beaches", "hiking", "mountains",
            "wildlife", "art", "museums", "architecture", "ramen", "temples"
        ]
        for kw in interest_keywords:
            if kw in lower:
                interests.append(kw)

        # 6. Travel Style & Accommodation
        travel_style: Optional[str] = None
        if "budget" in lower and "travel" in lower:
            travel_style = "Budget"
        elif "luxury" in lower or "5 star" in lower:
            travel_style = "Luxury"
        elif "balanced" in lower or "moderate" in lower:
            travel_style = "Balanced"
        elif "backpack" in lower:
            travel_style = "Backpacker"

        accommodation: Optional[str] = None
        if "hostel" in lower:
            accommodation = "Hostel"
        elif "resort" in lower:
            accommodation = "Resort"
        elif "hotel" in lower:
            accommodation = "Hotel"

        # 7. Food preferences
        food_preferences: List[str] = []
        if "vegetarian" in lower or "veg" in lower:
            food_preferences.append("Vegetarian")
        if "vegan" in lower:
            food_preferences.append("Vegan")
        if "halal" in lower:
            food_preferences.append("Halal")

        # 8. Constraints
        constraints: List[str] = []
        if "direct flight" in lower or "non-stop" in lower:
            constraints.append("Direct flights only")
        if "kid" in lower or "child" in lower:
            constraints.append("Kid-friendly")

        # 9. Deterministic Validation & Missing Requirements Identification
        if not destination:
            missing_fields.append("destination")
        if not origin:
            missing_fields.append("origin")
        if not duration and not (start_date and end_date):
            missing_fields.append("dates_or_duration")
        if not travelers:
            missing_fields.append("travelers")
        if budget is None:
            missing_fields.append("budget")

        # Validate Date sanity
        if start_date and end_date:
            try:
                s_dt = date.fromisoformat(start_date)
                e_dt = date.fromisoformat(end_date)
                if e_dt < s_dt:
                    conflicts.append(f"End date ({end_date}) is before start date ({start_date}).")
                else:
                    calculated_duration = (e_dt - s_dt).days + 1
                    if duration and duration != calculated_duration:
                        warnings.append(
                            f"Specified duration ({duration} days) adjusted to match calendar dates ({calculated_duration} days)."
                        )
                    duration = calculated_duration
            except ValueError as e:
                conflicts.append(f"Invalid date format: {str(e)}")

        # Validate Duration
        if duration is not None and duration <= 0:
            conflicts.append("Trip duration must be at least 1 day.")

        # Validate Travelers
        if travelers is not None and travelers <= 0:
            conflicts.append("Number of travelers must be at least 1.")

        # Validate Budget
        if budget is not None and budget < 0:
            conflicts.append("Trip budget cannot be negative.")

        # Clarification logic
        clarification_required = bool(missing_fields or conflicts)
        clarification_questions: List[str] = []

        if clarification_required:
            q_idx = 1
            if "destination" in missing_fields:
                clarification_questions.append(f"{q_idx}. Where would you like to travel?")
                q_idx += 1
            if "origin" in missing_fields:
                clarification_questions.append(f"{q_idx}. Where will you be departing from?")
                q_idx += 1
            if "dates_or_duration" in missing_fields:
                clarification_questions.append(f"{q_idx}. What dates or trip duration (in days) do you prefer?")
                q_idx += 1
            if "travelers" in missing_fields:
                clarification_questions.append(f"{q_idx}. How many travelers are joining this trip?")
                q_idx += 1
            if "budget" in missing_fields:
                clarification_questions.append(f"{q_idx}. What is your total estimated budget and currency?")
                q_idx += 1
            for conflict in conflicts:
                clarification_questions.append(f"{q_idx}. Conflict detected: {conflict} Please clarify.")
                q_idx += 1

        normalized_request = NormalizedTravelRequest(
            origin=origin,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            duration=duration,
            travelers=travelers,
            budget=budget,
            currency=currency,
            interests=interests,
            travel_style=travel_style,
            accommodation_preference=accommodation,
            food_preferences=food_preferences,
            constraints=constraints,
            additional_requirements=text.strip(),
        )

        return PlannerResult(
            extracted_requirements=normalized_request,
            missing_fields=missing_fields,
            conflicts=conflicts,
            assumptions=assumptions,
            warnings=warnings,
            clarification_required=clarification_required,
            clarification_questions=clarification_questions,
            is_demo=True,
        )


class LLMService:
    """Service providing provider-abstracted LLM execution and structured reasoning."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    @property
    def is_live_configured(self) -> bool:
        """Check if live LLM credentials are configured and not in DEMO_MODE."""
        return not self.settings.demo_mode and self.settings.has_llm_config

    def extract_plan(self, text: str, workflow_id: Optional[str] = None) -> PlannerResult:
        """Extract structured travel plan from natural language with model routing and caching.

        1. Checks intelligent cache to prevent duplicate LLM calls on identical prompts.
        2. In DEMO_MODE, routes deterministically to DemoPlannerExtractor.
        3. In live mode, uses ModelRouter (TaskType.PLANNER -> COMPLEX tier) with fallback protection.
        4. Records token usage and cost in CostTracker.
        """
        clean_text = text.strip()
        from utils.cache import intelligent_cache
        from utils.model_router import model_router, TaskType, WorkflowBudgetExceededError
        from utils.cost import cost_tracker

        # 1. Duplicate Call Prevention / Intelligent Cache
        cached_result = intelligent_cache.get("llm", "extract_plan", {"text": clean_text}, workflow_id=workflow_id)
        if cached_result:
            logger.info("[LLMService] Duplicate request intercepted: returning cached PlannerResult.")
            if isinstance(cached_result, dict):
                return PlannerResult.model_validate(cached_result)
            return cached_result

        # 2. DEMO_MODE Fallback
        if not self.is_live_configured:
            logger.info("[LLMService] DEMO_MODE active: using DemoPlannerExtractor.")
            result = DemoPlannerExtractor.extract(clean_text)
            intelligent_cache.set("llm", "extract_plan", {"text": clean_text}, result)
            return result

        # 3. Live Model Routing
        def _invoke_model(model_name: str) -> PlannerResult:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage

            llm = ChatOpenAI(
                model=model_name,
                api_key=self.settings.openai_api_key.get_secret_value(),
                temperature=0.0,
            )

            system_prompt = (
                "You are an expert travel planner agent. Extract structured travel specifications from the user's request. "
                "Analyze missing information (origin, destination, dates/duration, travelers, budget) and conflicting requirements. "
                "Return ONLY valid structured data matching the PlannerResult schema. "
                "Do NOT invent unstated requirements without recording safe assumptions."
            )

            structured_llm = llm.with_structured_output(PlannerResult)
            raw_res = structured_llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=clean_text),
            ])

            # Rough token attribution for tracking
            in_tokens = len(system_prompt.split()) + len(clean_text.split()) * 2
            out_tokens = 300
            cost_tracker.record_usage(
                model_name=model_name,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                agent_name="planner",
                workflow_id=workflow_id,
                task_type="planner",
                success=True,
            )

            if isinstance(raw_res, PlannerResult):
                self._validate_result_deterministically(raw_res)
                return raw_res

            parsed = PlannerResult.model_validate(raw_res)
            self._validate_result_deterministically(parsed)
            return parsed

        try:
            plan_result = model_router.execute_with_routing(
                task_type=TaskType.PLANNER,
                executable_fn=_invoke_model,
                agent_name="planner",
                workflow_id=workflow_id,
                max_retries=MAX_PLANNER_RETRIES,
            )
            intelligent_cache.set("llm", "extract_plan", {"text": clean_text}, plan_result)
            return plan_result
        except WorkflowBudgetExceededError as wbe:
            logger.warning(f"[LLMService] Workflow budget exceeded: {wbe}. Using deterministic fallback.")
            fallback = DemoPlannerExtractor.extract(clean_text)
            fallback.warnings.append(f"Workflow cost ceiling reached ({str(wbe)}). Deterministic extractor used to preserve budget.")
            return fallback
        except Exception as exc:
            logger.error(f"[LLMService] Live model routing failed: {exc}. Engaging DemoPlannerExtractor fallback.")
            fallback = DemoPlannerExtractor.extract(clean_text)
            fallback.warnings.append(f"Live model execution failed ({str(exc)}). Deterministic extractor used as fallback.")
            return fallback

    @staticmethod
    def _validate_result_deterministically(result: PlannerResult) -> None:
        """Perform strict deterministic cross-validation on LLM output."""
        req = result.extracted_requirements

        # Check critical fields
        missing = []
        if not req.destination:
            missing.append("destination")
        if not req.origin:
            missing.append("origin")
        if not req.duration and not (req.start_date and req.end_date):
            missing.append("dates_or_duration")
        if not req.travelers:
            missing.append("travelers")
        if req.budget is None:
            missing.append("budget")

        for m in missing:
            if m not in result.missing_fields:
                result.missing_fields.append(m)

        # Date validations
        if req.start_date and req.end_date:
            try:
                s = date.fromisoformat(req.start_date)
                e = date.fromisoformat(req.end_date)
                if e < s:
                    conflict_msg = f"End date ({req.end_date}) is before start date ({req.start_date})."
                    if conflict_msg not in result.conflicts:
                        result.conflicts.append(conflict_msg)
            except ValueError:
                result.conflicts.append("Invalid date format in extracted schedule.")

        # Traveler validations
        if req.travelers is not None and req.travelers <= 0:
            result.conflicts.append("Travelers must be at least 1.")

        # Budget validations
        if req.budget is not None and req.budget < 0:
            result.conflicts.append("Budget cannot be negative.")

        if result.missing_fields or result.conflicts:
            result.clarification_required = True
            if not result.clarification_questions:
                for f in result.missing_fields:
                    result.clarification_questions.append(f"Please provide missing parameter: {f}.")
                for c in result.conflicts:
                    result.clarification_questions.append(f"Conflict detected: {c}")


# Singleton instance
llm_service = LLMService()
