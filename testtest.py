import frontmatter
import markdown

with open("README.md", "r") as f:
    post = frontmatter.load(f)

# Metadata (parsed as a dictionary)
print(post.metadata)

# Original Markdown content (unmodified)
print(post.content)
print("\n")
print(markdown.markdown(post.content))
