from dify_plugin import DifyPluginEnv, Plugin

# A tool waits at most about four minutes for a run, inside the five-minute request limit; longer runs return
# their id for Get Generation.
plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=300))

if __name__ == "__main__":
    plugin.run()
