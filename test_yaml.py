import yaml

def test_load_yaml():
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        print(config)

if __name__ == "__main__":
    test_load_yaml()
