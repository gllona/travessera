"""
Parameter parser for extracting information from function signatures.

This module analyzes function signatures to determine which parameters
are path parameters, query parameters, or request body.
"""

import inspect
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, get_type_hints

from pydantic import BaseModel


@dataclass
class ParsedParameter:
    """Information about a function parameter."""

    name: str
    annotation: Any
    default: Any
    has_default: bool
    is_path_param: bool = False
    is_query_param: bool = False
    is_body_param: bool = False


@dataclass
class ParsedSignature:
    """Parsed function signature information."""

    parameters: Dict[str, ParsedParameter]
    path_params: List[str]
    query_params: List[str]
    body_param: Optional[str]
    return_type: Any


class ParameterParser:
    """
    Parses function signatures to extract parameter information.

    This parser determines:
    - Which parameters are path parameters (appear in the endpoint URL)
    - Which parameters are query parameters (not in path, for GET requests)
    - Which parameter is the request body (for POST/PUT/PATCH)
    """

    @staticmethod
    def parse_endpoint_path(path: str) -> Set[str]:
        """
        Extract parameter names from an endpoint path.

        Args:
            path: Endpoint path like "/users/{user_id}/posts/{post_id}"

        Returns:
            Set of parameter names found in the path
        """
        # Find all {param} patterns
        pattern = r"\{([^}]+)\}"
        matches = re.findall(pattern, path)
        return set(matches)

    @staticmethod
    def parse_function(
        func: Callable,
        endpoint_path: str,
        method: str,
    ) -> ParsedSignature:
        """
        Parse a function signature.

        Args:
            func: The function to parse
            endpoint_path: The endpoint path template
            method: The HTTP method

        Returns:
            Parsed signature information
        """
        # Get function signature
        sig = inspect.signature(func)

        # Get type hints (handles forward references better than sig.parameters)
        try:
            type_hints = get_type_hints(func)
        except Exception:
            # If get_type_hints fails, fall back to annotations
            type_hints = {}
            for name, param in sig.parameters.items():
                if param.annotation != inspect.Parameter.empty:
                    type_hints[name] = param.annotation

        # Get return type
        return_type = type_hints.get("return", sig.return_annotation)
        if return_type == inspect.Signature.empty:
            return_type = None

        # Extract path parameters from endpoint
        path_params = ParameterParser.parse_endpoint_path(endpoint_path)

        # Parse each parameter
        parameters = {}
        found_path_params = []
        query_params = []
        body_param = None

        for name, param in sig.parameters.items():
            # Skip self/cls parameters
            if name in ("self", "cls"):
                continue

            # Get type annotation
            annotation = type_hints.get(name, param.annotation)
            if annotation == inspect.Parameter.empty:
                annotation = Any

            # Check if has default
            has_default = param.default != inspect.Parameter.empty
            default = param.default if has_default else None

            # Create parsed parameter
            parsed = ParsedParameter(
                name=name,
                annotation=annotation,
                default=default,
                has_default=has_default,
            )

            # Determine parameter type
            if name in path_params:
                parsed.is_path_param = True
                found_path_params.append(name)
            elif method in ("POST", "PUT", "PATCH"):
                # For methods that typically have a body
                if ParameterParser._is_body_type(annotation):
                    if body_param is None:
                        parsed.is_body_param = True
                        body_param = name
                    else:
                        # Multiple body parameters - treat as query param
                        parsed.is_query_param = True
                        query_params.append(name)
                else:
                    # Simple types are query params even in POST
                    parsed.is_query_param = True
                    query_params.append(name)
            else:
                # GET, DELETE, etc - all non-path params are query params
                parsed.is_query_param = True
                query_params.append(name)

            parameters[name] = parsed

        # Validate all path params were found
        missing_params = path_params - set(found_path_params)
        if missing_params:
            raise ValueError(
                f"Path parameters {missing_params} not found in function signature"
            )

        return ParsedSignature(
            parameters=parameters,
            path_params=found_path_params,
            query_params=query_params,
            body_param=body_param,
            return_type=return_type,
        )

    @staticmethod
    def _is_body_type(annotation: Any) -> bool:
        """
        Check if a type annotation represents a body parameter.

        Body parameters are typically:
        - Pydantic models
        - Dict types
        - List types (for JSON arrays)

        Args:
            annotation: The type annotation

        Returns:
            True if this should be a body parameter
        """
        # Check if it's a Pydantic model
        if inspect.isclass(annotation) and issubclass(annotation, BaseModel):
            return True

        # Check for dict/list origins
        if hasattr(annotation, "__origin__"):
            origin = annotation.__origin__
            if origin in (dict, Dict, list, List):
                return True

        # Check if it's dict or list directly
        return annotation in (dict, list)

    @staticmethod
    def extract_path_values(
        path_template: str,
        parsed_sig: ParsedSignature,
        kwargs: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        """
        Extract path parameter values and build the final path.

        Args:
            path_template: Path template like "/users/{user_id}"
            parsed_sig: Parsed function signature
            kwargs: Function arguments

        Returns:
            Tuple of (formatted_path, remaining_kwargs)
        """
        path = path_template
        remaining_kwargs = kwargs.copy()

        # Replace each path parameter
        for param_name in parsed_sig.path_params:
            if param_name not in kwargs:
                param = parsed_sig.parameters[param_name]
                if param.has_default:
                    value = param.default
                else:
                    raise ValueError(f"Missing required path parameter: {param_name}")
            else:
                value = kwargs[param_name]
                remaining_kwargs.pop(param_name)

            # Replace in path
            path = path.replace(f"{{{param_name}}}", str(value))

        return path, remaining_kwargs

    @staticmethod
    def extract_query_params(
        parsed_sig: ParsedSignature,
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract query parameters from function arguments.

        Args:
            parsed_sig: Parsed function signature
            kwargs: Function arguments

        Returns:
            Dictionary of query parameters
        """
        query_params = {}

        for param_name in parsed_sig.query_params:
            if param_name in kwargs:
                value = kwargs[param_name]
                # Skip None values unless explicitly included
                if value is not None:
                    query_params[param_name] = value
            else:
                # Check for default value
                param = parsed_sig.parameters[param_name]
                if param.has_default and param.default is not None:
                    query_params[param_name] = param.default

        return query_params

    @staticmethod
    def extract_body_data(
        parsed_sig: ParsedSignature,
        kwargs: Dict[str, Any],
    ) -> Optional[Any]:
        """
        Extract request body data from function arguments.

        Args:
            parsed_sig: Parsed function signature
            kwargs: Function arguments

        Returns:
            The body data, or None if no body parameter
        """
        if parsed_sig.body_param and parsed_sig.body_param in kwargs:
            return kwargs[parsed_sig.body_param]
        return None
