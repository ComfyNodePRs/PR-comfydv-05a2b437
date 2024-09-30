import re
import json
import os
from typing import Any, Dict, List, Tuple
from aiohttp import web
from server import PromptServer  # from comfyui
import folder_paths  # from comfyui - gives access to `get_temp_directory()` and `get_output_directory()`
from jinja2 import Environment, sandbox, exceptions
import datetime
import random
import math
import sys
from rich import print
from rich.pretty import pprint

class FormatString:
    CATEGORY = "dv/string_operations"
    FUNCTION = "format_string"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("formatted_string", "saved_file_path")
    
    # Store configurations for each node instance
    node_configs = {}

    # Create a sandboxed Jinja2 environment for security
    jinja_env = sandbox.SandboxedEnvironment()

    # Define additional context
    def time_now() -> str:
        return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    additional_context = {
        "datetime": datetime,
        "now": time_now,
        "random": random,
        "math": math,
        # Add more modules or functions as needed
    }

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "template_type": (["Simple", "Jinja2"],),
                "template": ("STRING", {"multiline": True}),
                "save_path": ("STRING", {"default": ""}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID"
            }
        }
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        print("\n[bold red]IS_CHANGED:")
        pprint(kwargs)
        keys = cls._extract_keys(kwargs.get('template'))
        print("Keys:")
        pprint(keys)
        if kwargs.get('template_type', "simple") == "Jinja2":
            for k in cls.additional_context.keys():
                if k in kwargs.get('template'):
                    # assume that our additional context items are functions returning
                    # changing data such as datetime.now()
                    print(f"Detected: {k}")
                    return random.randrange(sys.maxsize)  # force to always recalc
        return kwargs

    @staticmethod
    def _extract_keys(template: str) -> List[str]:
        variables = []
        seen = set()

        def add_var(var):
            var = var.split('|')[0].split('.')[0].strip()
            if var not in seen and var not in FormatString.additional_context:
                seen.add(var)
                variables.append(var)

        # Extract variables from Jinja2 expressions {{ }}
        for match in re.finditer(r'\{\{\s*([\w.]+)(?:\|[\w\s]+)?(?:\.[^\(\)]+\(\))?\s*\}\}', template):
            add_var(match.group(1))

        # Extract variables from f-string style { }
        for match in re.finditer(r'\{(\w+)\}', template):
            add_var(match.group(1))

        # Extract variables from Jinja2 control structures {% %}
        for structure in re.finditer(r'\{%.*?%\}', template):
            for var in re.findall(r'\b(\w+)\|\b', structure.group(0)):
                if not var.startswith('end') and var not in {'if', 'else', 'elif', 'for', 'in'}:
                    add_var(var)

        return variables

    @classmethod
    def format_string(cls, template_type: str, template: str, save_path: str, **kwargs) -> Tuple[str, ...]:
        keys = cls._extract_keys(template)
        
        if template_type == "Simple":
            formatted_string = template.format(**kwargs)
        else:  # Jinja2
            try:
                jinja_template = cls.jinja_env.from_string(template)
                # Combine user-provided kwargs with additional_context
                context = {**cls.additional_context, **kwargs}
                formatted_string = jinja_template.render(**context)
            except exceptions.TemplateSyntaxError as e:
                formatted_string = f"Error in Jinja2 template: {str(e)}"
        
        # Save the state
        save_data = {
            "template_type": template_type,
            "template": template,
            "inputs": {k: kwargs.get(k, "") for k in keys}
        }
        
        if save_path:
            save_path = os.path.join(folder_paths.get_output_directory(), save_path)
            try:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "w") as f:
                    json.dump(save_data, f, indent=2, sort_keys=True)
                print(f"Node state saved to: {save_path}")
            except Exception as e:
                print(f"Error saving node state: {str(e)}")
                save_path = ""  # Reset save_path if saving failed
        else:
            print("No save_path provided, node state not saved.")
        
        # Return all input values first, then formatted_string and saved_file_path
        return tuple(str(kwargs.get(key, "")) for key in keys) + (formatted_string, save_path)

    @classmethod
    def update_widget(cls, node_id: str, template_type: str, template: str) -> Dict[str, Any]:
        keys = cls._extract_keys(template)
        config = {
            "inputs": {
                "template_type": (["Simple", "Jinja2"],),
                "template": ("STRING", {"multiline": True}),
                "save_path": ("STRING", {"default": ""}),
            },
            "outputs": [],
        }
        for key in keys:
            config["inputs"][key] = ("STRING", {"default": ""})
            config["outputs"].append({"name": key, "type": "STRING"})
        
        # Add formatted_string and saved_file_path at the end of outputs
        config["outputs"].extend([
            {"name": "formatted_string", "type": "STRING"},
            {"name": "saved_file_path", "type": "STRING"},
        ])
        
        # Update RETURN_TYPES and RETURN_NAMES
        cls.RETURN_TYPES = ("STRING",) * len(keys) + ("STRING", "STRING")
        cls.RETURN_NAMES = tuple(keys) + ("formatted_string", "saved_file_path")
        
        # Store the configuration for this specific node
        cls.node_configs[node_id] = config
        
        return config

    @classmethod
    def get_node_config(cls, node_id: str) -> Dict[str, Any]:
        return cls.node_configs.get(node_id, {})

    @classmethod
    def load_node_state(cls, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r") as f:
                load_data = json.load(f)
            return load_data
        except FileNotFoundError:
            return {}
        except Exception as e:
            print(f"Error loading node state: {e}")
            return {}

# Custom route for updating node configuration
@PromptServer.instance.routes.post("/update_format_string_node")
async def update_format_string_node(request):
    data = await request.json()
    node_id = data.get('nodeId', '')
    template_type = data.get('template_type', '')
    template = data.get('template', '')
    updated_config = FormatString.update_widget(node_id, template_type, template)
    return web.json_response(updated_config)

# Custom route for loading node state
@PromptServer.instance.routes.post("/load_format_string_node")
async def load_format_string_node(request):
    data = await request.json()
    file_path = data.get('file_path', '')
    state = FormatString.load_node_state(file_path)
    return web.json_response(state)

# Custom route for getting node-specific configuration
@PromptServer.instance.routes.get("/get_format_string_node_config/{node_id}")
async def get_format_string_node_config(request):
    node_id = request.match_info['node_id']
    config = FormatString.get_node_config(node_id)
    return web.json_response(config)

NODE_CLASS_MAPPINGS = {
    "FormatString": FormatString
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FormatString": "Format String"
}