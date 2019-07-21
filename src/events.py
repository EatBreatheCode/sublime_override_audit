import sublime
import sublime_plugin
import os

from .core import override_group, delete_packed_override
from ..lib.packages import check_potential_override



class OverrideAuditEventListener(sublime_plugin.EventListener):
	"""
	Check on file load and save to see if the new file is potentially an
	override for a package, and set the variables that allow for our context
	menus to let you edit/diff the override.
	"""
	def _check_for_override(self, view):
		filename = view.file_name()
		if filename is None or not os.path.isfile(filename):
			return

		result = check_potential_override(filename, deep=True)
		if result is not None:
			override_group.apply(view, result[0], result[1], False)
		else:
			override_group.remove(view)

	def on_post_save_async(self, view):
		# Will remove existing settings if the view is no longer an override
		self._check_for_override(view)

	def on_load_async(self, view):
		# Things like PackageResourceViewer trigger on_load before the file
		# actually exists; context items are only allowed once the file is
		# actually saved.
		self._check_for_override(view)

	def on_close(self, view):
		tmp_base = view.settings().get("_oa_ext_diff_base", None)
		if tmp_base is not None:
			delete_packed_override(tmp_base)




class CreateOverrideEventListener(sublime_plugin.ViewEventListener):
	"""
	This listener applies only to newly created override views created by the
	override_audit_create_override command. It ensures that the appropriate
	path exists prior to saving a new override, and removes the scratch mark
	from a new override once it has been modified for the first time.
	"""
	@classmethod
	def is_applicable(cls, settings):
		return settings.get("_oa_is_new_override", False)

	def on_pre_save(self):
		"""
		Before the first save of a new override, try to create the appropriate
		unpacked folder; doing so marked this as no longer a potential new
		override.
		"""
		path = os.path.dirname(self.view.file_name())
		try:
			os.makedirs(path, exist_ok=True)
			self.view.settings().erase("_oa_is_new_override")
		except:
			log("Error creating package directory for new override",
				dialog=True)

	def on_modified(self):
		"""
		On first modification to the buffer, turn off the scratch status so the
		user knows they modified the original file.
		"""
		if self.view.is_scratch():
			self.view.set_scratch(False)