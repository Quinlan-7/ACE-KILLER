use serde::{Deserialize, Serialize};
use crate::config::Config;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessAction {
    #[serde(rename = "type")]
    pub action_type: String,
    pub value: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessRule {
    pub name: String,
    pub process_pattern: String,
    pub match_type: String,
    pub actions: Vec<ProcessAction>,
    pub enabled: bool,
    pub profile_name: Option<String>,
    pub created_at: String,
    pub description: String,
}

pub struct RuleEngine {
    pub rules: Vec<ProcessRule>,
}

impl RuleEngine {
    pub fn new(config: &Config) -> Self {
        let rules: Vec<ProcessRule> = config
            .rules
            .iter()
            .filter_map(|r| serde_json::from_value(r.clone()).ok())
            .collect();
        Self { rules }
    }

    pub fn list_rules(&self) -> Vec<ProcessRule> {
        self.rules.clone()
    }

    pub fn add_rule(&mut self, rule: ProcessRule) {
        self.rules.push(rule);
    }

    pub fn remove_rule(&mut self, name: &str) {
        self.rules.retain(|r| r.name != name);
    }

    pub fn get_matching_rules(&self, process_name: &str) -> Vec<&ProcessRule> {
        self.rules
            .iter()
            .filter(|r| r.enabled && self.match_process(&r.process_pattern, process_name, &r.match_type))
            .collect()
    }

    fn match_process(&self, pattern: &str, name: &str, match_type: &str) -> bool {
        match match_type {
            "exact" => pattern.eq_ignore_ascii_case(name),
            "wildcard" => {
                let wildcard_pattern = pattern.replace("*", ".*").replace("?", ".");
                regex::Regex::new(&format!("(?i)^{}$", wildcard_pattern))
                    .map(|re| re.is_match(name))
                    .unwrap_or(false)
            }
            "regex" => regex::Regex::new(pattern)
                .map(|re| re.is_match(name))
                .unwrap_or(false),
            _ => false,
        }
    }

    pub fn save(&self, config: &Config) -> Result<(), String> {
        let mut cfg = config.clone();
        cfg.rules = self.rules.iter().map(|r| serde_json::to_value(r).unwrap()).collect();
        cfg.save()
    }
}
